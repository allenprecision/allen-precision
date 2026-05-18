import io
import base64
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

# Column order for Altera / Matrixify order import format
COLUMNS = [
    'Name',
    'Email',
    'Financial Status',
    'Fulfillment Status',
    'Currency',
    'Subtotal',
    'Shipping',
    'Taxes',
    'Total',
    'Created at',
    'Notes',
    'Tags',
    'Phone',
    'Lineitem name',
    'Lineitem sku',
    'Lineitem quantity',
    'Lineitem price',
    'Lineitem requires shipping',
    'Lineitem taxable',
    'Billing Name',
    'Billing Address1',
    'Billing Address2',
    'Billing City',
    'Billing Zip',
    'Billing Province',
    'Billing Country',
    'Billing Phone',
    'Shipping Name',
    'Shipping Address1',
    'Shipping Address2',
    'Shipping City',
    'Shipping Zip',
    'Shipping Province',
    'Shipping Country',
    'Shipping Phone',
    'Tax 1 Title',
    'Tax 1 Price',
    'Tax 1 Rate',
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
]

COL_IDX = {name: idx for idx, name in enumerate(COLUMNS)}


class ShopifyOrderExportWizard(models.TransientModel):
    _name = 'shopify.order.export.wizard'
    _description = 'Export Orders to Shopify — Altera / Matrixify Format'

    offset = fields.Integer(
        string='Skip first N orders',
        default=0,
        help='0 = first 1000 orders, 1000 = next 1000, 2000 = third batch, etc.',
    )
    only_unexported = fields.Boolean(
        string='Only unexported orders',
        default=True,
        help='If checked, only orders not yet exported to Shopify are included.',
    )
    record_count = fields.Integer(string='Orders in this batch', readonly=True)
    file_data = fields.Binary(string='Download Excel', readonly=True, attachment=False)
    file_name = fields.Char(readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')

    def action_generate(self):
        self.ensure_one()

        if not HAS_XLSXWRITER:
            raise UserError(_('xlsxwriter is not installed on this server.'))

        domain = [('state', '=', 'sale')]
        if self.only_unexported:
            domain.append(('is_exported_to_shopify', '=', False))

        orders = self.env['sale.order'].search(
            domain,
            order='date_order asc, id asc',
            limit=1000,
            offset=self.offset,
        )

        if not orders:
            raise UserError(_('No orders found for the selected criteria and offset.'))

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
            partner         = order.partner_id
            inv_partner     = order.partner_invoice_id or partner
            ship_partner    = order.partner_shipping_id or partner

            # First tax on any taxed line
            tax_title, tax_price, tax_rate = '', order.amount_tax, 0.0
            for ol in order.order_line:
                if ol.tax_id:
                    t = ol.tax_id[0]
                    tax_title = t.name
                    tax_rate  = round(t.amount / 100.0, 6)
                    break

            # Order-level data (written only on first line-item row)
            order_row = {
                'Name':              order.name,
                'Email':             partner.email or '',
                'Financial Status':  'paid' if order.invoice_status == 'invoiced' else 'pending',
                'Fulfillment Status': '',
                'Currency':          order.currency_id.name or '',
                'Subtotal':          order.amount_untaxed,
                'Shipping':          0,
                'Taxes':             order.amount_tax,
                'Total':             order.amount_total,
                'Created at':        order.date_order.strftime('%Y-%m-%d %H:%M:%S') if order.date_order else '',
                'Notes':             html2plaintext(order.note or ''),
                'Tags':              'Exported from Odoo',
                'Phone':             partner.phone or partner.mobile or '',
                'Billing Name':      inv_partner.name or '',
                'Billing Address1':  inv_partner.street or '',
                'Billing Address2':  inv_partner.street2 or '',
                'Billing City':      inv_partner.city or '',
                'Billing Zip':       inv_partner.zip or '',
                'Billing Province':  inv_partner.state_id.name if inv_partner.state_id else '',
                'Billing Country':   inv_partner.country_id.name if inv_partner.country_id else '',
                'Billing Phone':     inv_partner.phone or '',
                'Shipping Name':     ship_partner.name or '',
                'Shipping Address1': ship_partner.street or '',
                'Shipping Address2': ship_partner.street2 or '',
                'Shipping City':     ship_partner.city or '',
                'Shipping Zip':      ship_partner.zip or '',
                'Shipping Province': ship_partner.state_id.name if ship_partner.state_id else '',
                'Shipping Country':  ship_partner.country_id.name if ship_partner.country_id else '',
                'Shipping Phone':    ship_partner.phone or '',
                'Tax 1 Title':       tax_title,
                'Tax 1 Price':       tax_price,
                'Tax 1 Rate':        tax_rate,
                # Metafields
                'Metafield: custom.po [boolean]':                          'TRUE' if order.po_processed else 'FALSE',
                'Metafield: custom.processed [boolean]':                   'TRUE' if order.processed else 'FALSE',
                'Metafield: custom.payment_status [boolean]':              'TRUE' if order.pay_processed else 'FALSE',
                'Metafield: custom.order_id [number_integer]':             order.id,
                'Metafield: custom.delivery_date [date_time]':             order.commitment_date.isoformat() if order.commitment_date else '',
                'Metafield: custom.sales_agent [single_line_text_field]':  order.sales_agent.name if order.sales_agent else '',
                'Metafield: custom.client_order_ref [single_line_text_field]': order.client_order_ref or '',
                'Metafield: custom.fiscal_position_id [single_line_text_field]': order.fiscal_position_id.name if order.fiscal_position_id else '',
                'Metafield: custom.incoterm [single_line_text_field]':     order.incoterm.code if order.incoterm else '',
                'Metafield: custom.incoterm_location [single_line_text_field]': order.incoterm_location or '',
                'Metafield: custom.team_id [single_line_text_field]':      order.team_id.name if order.team_id else '',
                'Metafield: custom.user_id [single_line_text_field]':      order.user_id.name if order.user_id else '',
                'Metafield: custom.partner_id [single_line_text_field]':   order.partner_id.ref or '',
                'Metafield: custom.pricelist_id [single_line_text_field]': order.pricelist_id.name if order.pricelist_id else '',
                'Metafield: custom.picking_policy [single_line_text_field]': order.picking_policy or '',
                'Metafield: custom.exemption_code [single_line_text_field]': order.exemption_code or '',
                'Metafield: custom.exemption_code_id [single_line_text_field]': order.exemption_code_id.code if order.exemption_code_id else '',
                'Metafield: custom.source_id [single_line_text_field]':    order.source_id.name if order.source_id else '',
                'Metafield: custom.medium_id [single_line_text_field]':    order.medium_id.name if order.medium_id else '',
                'Metafield: custom.campaign_id [single_line_text_field]':  order.campaign_id.name if order.campaign_id else '',
            }

            valid_lines = [l for l in order.order_line if not l.display_type and l.product_id]
            if not valid_lines:
                self._write_row(ws, row, order_row, lineitem_name='', lineitem_sku='',
                                lineitem_qty=0, lineitem_price=0,
                                requires_shipping=False, taxable=False)
                row += 1
                continue

            for i, line in enumerate(valid_lines):
                requires_shipping = line.product_id.type in ('product', 'consu')
                taxable           = bool(line.tax_id)
                if i == 0:
                    self._write_row(ws, row, order_row,
                                    lineitem_name=line.name or line.product_id.display_name,
                                    lineitem_sku=line.product_id.default_code or '',
                                    lineitem_qty=int(line.product_uom_qty),
                                    lineitem_price=line.price_unit,
                                    requires_shipping=requires_shipping,
                                    taxable=taxable)
                else:
                    # Subsequent line items — only Name + lineitem columns
                    self._write_row(ws, row, {'Name': order.name},
                                    lineitem_name=line.name or line.product_id.display_name,
                                    lineitem_sku=line.product_id.default_code or '',
                                    lineitem_qty=int(line.product_uom_qty),
                                    lineitem_price=line.price_unit,
                                    requires_shipping=requires_shipping,
                                    taxable=taxable)
                row += 1

        wb.close()
        output.seek(0)

        fname = f'shopify_orders_{self.offset + 1}_to_{self.offset + len(orders)}.xlsx'
        self.write({
            'file_data':    base64.b64encode(output.read()),
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

    def action_reset(self):
        self.write({'state': 'draft', 'file_data': False, 'file_name': False, 'record_count': 0})
        return {
            'type':      'ir.actions.act_window',
            'res_model': self._name,
            'res_id':    self.id,
            'view_mode': 'form',
            'target':    'new',
        }

    @staticmethod
    def _write_row(ws, row, data, lineitem_name, lineitem_sku,
                   lineitem_qty, lineitem_price, requires_shipping, taxable):
        row_data = dict(data)
        row_data['Lineitem name']              = lineitem_name
        row_data['Lineitem sku']               = lineitem_sku
        row_data['Lineitem quantity']          = lineitem_qty
        row_data['Lineitem price']             = lineitem_price
        row_data['Lineitem requires shipping'] = 'TRUE' if requires_shipping else 'FALSE'
        row_data['Lineitem taxable']           = 'TRUE' if taxable else 'FALSE'
        for col, val in row_data.items():
            idx = COL_IDX.get(col)
            if idx is not None:
                ws.write(row, idx, val)
