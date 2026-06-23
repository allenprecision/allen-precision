import io
import base64
import zipfile
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False

# Exact column order matching Altera export format
COLUMNS = [
    'Name',
    'Command',
    'Send Receipt',
    'Inventory Behaviour',
    'Phone',
    'Email',
    'Note',
    'Tags',
    'Tags Command',
    'Created At',
    'Processed At',
    'Currency',
    'Price: Total Line Items',
    'Price: Subtotal',
    'Tax 1: Title',
    'Tax 1: Rate',
    'Tax 1: Price',
    'Tax: Included',
    'Tax: Total',
    'Price: Total Discount',
    'Price: Total Shipping',
    'Price: Total',
    'Payment: Status',
    'Order Fulfillment Status',
    'Purchase Order Number',
    'Customer: ID',
    'Customer: Email',
    'Billing: First Name',
    'Billing: Last Name',
    'Billing: Name',
    'Billing: Company',
    'Billing: Phone',
    'Billing: Address 1',
    'Billing: Address 2',
    'Billing: Zip',
    'Billing: City',
    'Billing: Province',
    'Billing: Province Code',
    'Billing: Country',
    'Billing: Country Code',
    'Shipping: First Name',
    'Shipping: Last Name',
    'Shipping: Name',
    'Shipping: Company',
    'Shipping: Phone',
    'Shipping: Address 1',
    'Shipping: Address 2',
    'Shipping: Zip',
    'Shipping: City',
    'Shipping: Province',
    'Shipping: Province Code',
    'Shipping: Country',
    'Shipping: Country Code',
    'Row #',
    'Top Row',
    'Line: Type',
    'Line: Command',
    'Line: Title',
    'Line: Name',
    'Line: Variant ID',
    'Line: SKU',
    'Line: Quantity',
    'Line: Price',
    'Line: Requires Shipping',
    'Line: Taxable',
    # Metafields
    'Metafield: custom.po [boolean]',
    'Metafield: custom.processed [boolean]',
    'Metafield: custom.payment_status [boolean]',
    'Metafield: custom.order_id [number_integer]',
    'Metafield: custom.delivery_date [date_time]',
    'Metafield: custom.sales_agent [single_line_text_field]',
    'Metafield: custom.client_order_ref [single_line_text_field]',
    'Metafield: custom.fiscal_position_id [single_line_text_field]',
    'Metafield: custom.incoterm [single_line_text_field]',
    'Metafield: custom.incoterm_location [single_line_text_field]',
    'Metafield: custom.team_id [single_line_text_field]',
    'Metafield: custom.user_id [single_line_text_field]',
    'Metafield: custom.partner_id [single_line_text_field]',
    'Metafield: custom.pricelist_id [single_line_text_field]',
    'Metafield: custom.picking_policy [single_line_text_field]',
    'Metafield: custom.exemption_code [single_line_text_field]',
    'Metafield: custom.exemption_code_id [single_line_text_field]',
    'Metafield: custom.source_id [single_line_text_field]',
    'Metafield: custom.medium_id [single_line_text_field]',
    'Metafield: custom.campaign_id [single_line_text_field]',
    'Metafield: custom.opportunity_id [single_line_text_field]',
]

COL_IDX = {name: idx for idx, name in enumerate(COLUMNS)}


def _split_name(name):
    parts = (name or '').strip().split(' ', 1)
    return parts[0], (parts[1] if len(parts) > 1 else '')


def _address_data(partner, prefix):
    if not (partner.street and partner.city and partner.country_id):
        return {}
    fn, ln = _split_name(partner.name)
    return {
        f'{prefix}: First Name':    fn,
        f'{prefix}: Last Name':     ln,
        f'{prefix}: Name':          partner.name or '',
        f'{prefix}: Company':       partner.parent_id.name if partner.parent_id else '',
        f'{prefix}: Phone':         partner.phone or '',
        f'{prefix}: Address 1':     partner.street or '',
        f'{prefix}: Address 2':     partner.street2 or '',
        f'{prefix}: Zip':           partner.zip or '',
        f'{prefix}: City':          partner.city or '',
        f'{prefix}: Province':      partner.state_id.name if partner.state_id else '',
        f'{prefix}: Province Code': partner.state_id.code if partner.state_id else '',
        f'{prefix}: Country':       partner.country_id.name if partner.country_id else '',
        f'{prefix}: Country Code':  partner.country_id.code if partner.country_id else '',
    }


def _address_data_with_fallback(preferred, fallbacks, prefix):
    for p in [preferred] + list(fallbacks):
        result = _address_data(p, prefix)
        if result:
            return result
    return {}


class ShopifyOrderExportWizard(models.TransientModel):
    _name = 'shopify.order.export.wizard'
    _description = 'Export Orders to Shopify — Altera Format'

    offset = fields.Integer(
        string='Skip first N orders',
        default=0,
        help='0 = first batch, 10 = second batch, 20 = third, etc.',
    )
    batch_size = fields.Integer(
        string='Records per file',
        default=1000,
        help='Max 1000 orders per file.',
    )
    only_unexported = fields.Boolean(
        string='Only unexported orders',
        default=True,
    )
    record_count = fields.Integer(string='Orders in this file', readonly=True)
    file_data = fields.Binary(string='Download Excel', readonly=True, attachment=False)
    file_name = fields.Char(readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')

    # ─────────────────────────────────────────────────────────────────────────
    # Public actions
    # ─────────────────────────────────────────────────────────────────────────

    def action_generate(self):
        """Standard mode: generate one Matrixify file using batch_size / offset."""
        self.ensure_one()
        if not HAS_XLSXWRITER:
            raise UserError(_('xlsxwriter is not installed on this server.'))

        domain = [('state', '=', 'sale')]
        if self.only_unexported:
            domain.append(('is_exported_to_shopify', '=', False))

        orders = self.env['sale.order'].search(
            domain,
            order='date_order desc, id desc',
            limit=self.batch_size,
            offset=self.offset,
        )
        if not orders:
            raise UserError(_('No orders found for the selected criteria and offset.'))

        xlsx_bytes = self._build_matrixify_xlsx(orders)
        fname = f'shopify_orders_{self.offset + 1}_to_{self.offset + len(orders)}.xlsx'
        self.write({
            'file_data':    base64.b64encode(xlsx_bytes),
            'file_name':    fname,
            'record_count': len(orders),
            'state':        'done',
        })
        return {
            'type':      'ir.actions.act_window',
            'res_model': self._name,
            'res_id':    self.id,
            'view_mode': 'form',
            'target':    'new',
        }

    def action_generate_bulk(self):
        """Generate Matrixify files for ALL matching orders and return as a ZIP download."""
        self.ensure_one()
        if not HAS_XLSXWRITER:
            raise UserError(_('xlsxwriter is not installed on this server.'))

        domain = [('state', '=', 'sale')]
        if self.only_unexported:
            domain.append(('is_exported_to_shopify', '=', False))

        all_orders = self.env['sale.order'].search(domain, order='date_order desc, id desc')
        if not all_orders:
            raise UserError(_('No confirmed sale orders found.'))

        batch_size = min(self.batch_size or 1000, 1000)
        _logger.info('Shopify bulk export: %d orders found, generating files of %d each.',
                     len(all_orders), batch_size)

        zip_buffer = io.BytesIO()
        order_list = list(all_orders)
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i in range(0, len(order_list), batch_size):
                batch = order_list[i: i + batch_size]
                records = self.env['sale.order'].browse([o.id for o in batch])
                xlsx_bytes = self._build_matrixify_xlsx(records)
                file_num = i // batch_size + 1
                fname = f'shopify_batch_{file_num:03d}_{batch[0].name}_to_{batch[-1].name}.xlsx'
                zf.writestr(fname, xlsx_bytes)

        zip_buffer.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': 'shopify_matrixify_all_orders.zip',
            'type': 'binary',
            'datas': base64.b64encode(zip_buffer.read()),
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type':   'ir.actions.act_url',
            'url':    f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_reset(self):
        self.write({'state': 'draft', 'file_data': False, 'file_name': False, 'record_count': 0})
        return {
            'type':      'ir.actions.act_window',
            'res_model': self._name,
            'res_id':    self.id,
            'view_mode': 'form',
            'target':    'new',
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Core builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_matrixify_xlsx(self, orders):
        """Build one Matrixify-format XLSX for the given sale.order recordset.
        Returns raw bytes."""
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Orders')

        hdr_fmt = wb.add_format({
            'bold': True,
            'bg_color': '#1F497D',
            'font_color': '#FFFFFF',
            'border': 1,
        })
        for idx, col in enumerate(COLUMNS):
            ws.write(0, idx, col, hdr_fmt)
            ws.set_column(idx, idx, max(14, len(col) + 2))

        row = 1
        for order in orders:
            partner = order.partner_id
            inv_p   = order.partner_invoice_id or partner
            ship_p  = order.partner_shipping_id or partner

            tax_title, tax_rate, tax_price = '', 0.0, order.amount_tax
            for ol in order.order_line:
                if ol.tax_id:
                    t = ol.tax_id[0]
                    tax_title = t.name
                    tax_rate  = round(t.amount / 100.0, 6)
                    break

            shipping_total = sum(
                ol.price_subtotal for ol in order.order_line
                if not ol.display_type and getattr(ol, 'is_delivery', False)
            )

            billing_addr  = _address_data_with_fallback(inv_p,  [partner], 'Billing')
            shipping_addr = _address_data_with_fallback(ship_p, [inv_p, partner], 'Shipping')

            if not billing_addr:
                _logger.warning(
                    "Shopify export: skipping order %s — no valid billing address on '%s'.",
                    order.name, partner.name,
                )
                continue

            order_data = {
                'Name':                    order.name,
                'Command':                 'NEW',
                'Send Receipt':            False,
                'Inventory Behaviour':     'bypass',
                'Phone':                   partner.phone or partner.mobile or '',
                'Email':                   partner.email or '',
                'Note':                    html2plaintext(order.note or ''),
                'Tags':                    'Exported from Odoo',
                'Tags Command':            'REPLACE',
                'Created At':              order.date_order.strftime('%Y-%m-%d %H:%M:%S') if order.date_order else '',
                'Processed At':            order.date_order.strftime('%Y-%m-%d %H:%M:%S') if order.date_order else '',
                'Currency':                order.currency_id.name or 'USD',
                'Price: Total Line Items': order.amount_untaxed,
                'Price: Subtotal':         order.amount_untaxed,
                'Tax 1: Title':            tax_title,
                'Tax 1: Rate':             tax_rate,
                'Tax 1: Price':            tax_price,
                'Tax: Included':           False,
                'Tax: Total':              order.amount_tax,
                'Price: Total Discount':   0,
                'Price: Total Shipping':   shipping_total,
                'Price: Total':            order.amount_total,
                'Payment: Status':         'paid' if order.invoice_status == 'invoiced' else 'pending',
                'Order Fulfillment Status': '',
                'Purchase Order Number':   order.client_order_ref or '',
                'Customer: ID':            partner.shopify_customer_id or '',
                'Customer: Email':         partner.email or '',
                **billing_addr,
                **shipping_addr,
                'Metafield: custom.po [boolean]':                              'true' if order.po_processed else 'false',
                'Metafield: custom.processed [boolean]':                       'true' if order.processed else 'false',
                'Metafield: custom.payment_status [boolean]':                  'true' if order.pay_processed else 'false',
                'Metafield: custom.order_id [number_integer]':                 order.id,
                'Metafield: custom.delivery_date [date_time]':                 order.commitment_date.isoformat() if order.commitment_date else '',
                'Metafield: custom.sales_agent [single_line_text_field]':      order.sales_agent.name if order.sales_agent else '',
                'Metafield: custom.client_order_ref [single_line_text_field]': order.client_order_ref or '',
                'Metafield: custom.fiscal_position_id [single_line_text_field]': order.fiscal_position_id.name if order.fiscal_position_id else '',
                'Metafield: custom.incoterm [single_line_text_field]':         order.incoterm.name if order.incoterm else '',
                'Metafield: custom.incoterm_location [single_line_text_field]': order.incoterm_location or '',
                'Metafield: custom.team_id [single_line_text_field]':          order.team_id.name if order.team_id else '',
                'Metafield: custom.user_id [single_line_text_field]':          order.user_id.name if order.user_id else '',
                'Metafield: custom.partner_id [single_line_text_field]':       order.partner_id.ref or '',
                'Metafield: custom.pricelist_id [single_line_text_field]':     order.pricelist_id.name if order.pricelist_id else '',
                'Metafield: custom.picking_policy [single_line_text_field]':   order.picking_policy or '',
                'Metafield: custom.exemption_code [single_line_text_field]':   order.exemption_code or '',
                'Metafield: custom.exemption_code_id [single_line_text_field]': order.exemption_code_id.code if order.exemption_code_id else '',
                'Metafield: custom.source_id [single_line_text_field]':        order.source_id.name if order.source_id else '',
                'Metafield: custom.medium_id [single_line_text_field]':        order.medium_id.name if order.medium_id else '',
                'Metafield: custom.campaign_id [single_line_text_field]':      order.campaign_id.name if order.campaign_id else '',
                'Metafield: custom.opportunity_id [single_line_text_field]':   order.opportunity_id.name if order.opportunity_id else '',
            }

            valid_lines = [
                l for l in order.order_line
                if not l.display_type and l.product_id and l.product_uom_qty > 0
            ]
            if not valid_lines:
                continue

            for i, line in enumerate(valid_lines):
                prod  = line.product_id
                ptavs = prod.product_template_attribute_value_ids
                if ptavs:
                    variant_opts = " / ".join(
                        ptav.product_attribute_value_id.name for ptav in ptavs
                    )
                    line_name = f"{prod.name} - {variant_opts}"
                else:
                    line_name = prod.name or ''

                vid_raw = prod.shopify_variant_id or ''
                vid = vid_raw.split('/')[-1] if vid_raw else ''

                self._write_row(
                    ws, row,
                    order_data if i == 0 else {'Name': order.name},
                    row_num=i + 1,
                    top_row=(i == 0),
                    title=prod.name or '',
                    line_name=line_name,
                    variant_id=vid,
                    sku='' if vid else (prod.default_code or ''),
                    qty=max(1, round(line.product_uom_qty)),
                    price=line.price_unit,
                    requires_shipping=line.product_id.type in ('product', 'consu'),
                    taxable=bool(line.tax_id),
                )
                row += 1

        wb.close()
        output.seek(0)
        return output.read()

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _write_row(ws, row, data, row_num, top_row,
                   title, line_name, variant_id, sku, qty, price,
                   requires_shipping, taxable):
        row_data = dict(data)
        row_data['Row #']                   = row_num
        row_data['Top Row']                 = True if top_row else None
        row_data['Line: Type']              = 'Line Item'
        row_data['Line: Command']           = 'DEFAULT'
        row_data['Line: Title']             = title
        row_data['Line: Name']              = line_name
        row_data['Line: Variant ID']        = variant_id
        row_data['Line: SKU']               = sku
        row_data['Line: Quantity']          = qty
        row_data['Line: Price']             = price
        row_data['Line: Requires Shipping'] = requires_shipping
        row_data['Line: Taxable']           = taxable
        for col, val in row_data.items():
            idx = COL_IDX.get(col)
            if idx is not None:
                ws.write(row, idx, val)
