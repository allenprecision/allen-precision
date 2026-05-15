from odoo import models, fields, _
from odoo.exceptions import UserError
import requests
import json
import re
import logging

_logger = logging.getLogger(__name__)
API = "2024-01"


class _OrderAlreadyExistsError(Exception):
    pass


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopify_order_id = fields.Char(string='Shopify Order ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)

    # ─────────────────────────────────────────────────────────────────────────
    # Public action
    # ─────────────────────────────────────────────────────────────────────────

    def action_export_to_shopify(self):
        success_orders = []
        existing_orders = []
        error_messages = []

        already_exported = self.filtered(lambda o: o.is_exported_to_shopify and o.shopify_order_id)
        orders_to_export = self - already_exported

        for order in orders_to_export:
            try:
                order._export_to_shopify()
                success_orders.append(order.name)
            except _OrderAlreadyExistsError:
                existing_orders.append(order.name)
            except Exception as e:
                error_messages.append(f"{order.name}: {e}")

        message_parts = []
        if success_orders:
            message_parts.append(_("Orders exported successfully: %s") % ", ".join(success_orders[:10]))
        if already_exported:
            message_parts.append(_("Already exported (skipped): %s") % ", ".join(already_exported.mapped('name')))
        if existing_orders:
            message_parts.append(_("Already exists in Shopify: %s") % ", ".join(existing_orders))
        if error_messages:
            message_parts.append("\n".join(error_messages[:5]))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Sync Results'),
                'message': "\n\n".join(message_parts),
                'type': 'success' if not error_messages else 'warning',
                'sticky': bool(error_messages),
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Core export
    # ─────────────────────────────────────────────────────────────────────────

    def _export_to_shopify(self):
        self.ensure_one()

        instance = self._resolve_instance()
        session = self._make_session(instance)
        shop_url = (instance.shop_url or "").replace('https://', '').replace('http://', '').strip('/')

        # ── 1. Ensure customer exists on Shopify ──────────────────────────────
        partner = self.partner_id
        if not partner.shopify_customer_id:
            if partner.cant_export_to_shopify:
                raise UserError(
                    _("Customer '%s' is blocked from Shopify export (cant_export_to_shopify is set).")
                    % partner.name
                )
            if not partner.shopify_instance_id:
                partner.shopify_instance_id = instance.id
            try:
                partner._export_to_shopify(session, instance)
            except Exception as e:
                raise UserError(_("Auto-export of customer '%s' failed: %s") % (partner.name, e))

        # ── 2. Duplicate order guard ──────────────────────────────────────────
        if self.shopify_order_id:
            check = session.get(
                f"https://{shop_url}/admin/api/{API}/orders/{self.shopify_order_id}.json",
                timeout=20,
            )
            if check.status_code == 200:
                raise _OrderAlreadyExistsError()
            elif check.status_code == 404:
                _logger.warning("Shopify order ID %s stale for '%s' — recreating.", self.shopify_order_id, self.name)
                self.write({'shopify_order_id': False, 'is_exported_to_shopify': False})
            else:
                raise UserError(
                    _("Failed to verify Shopify order for %s. Status %s: %s")
                    % (self.name, check.status_code, check.text[:300])
                )

        # ── 3. Build line items ───────────────────────────────────────────────
        line_items = []
        for line in self.order_line:
            if line.display_type or not line.product_id:
                continue
            variant_id = line.product_id.shopify_variant_id
            item = {
                "quantity": int(line.product_uom_qty),
                "price":    str(line.price_unit),
                "title":    line.name or line.product_id.display_name,
            }
            if variant_id:
                try:
                    item["variant_id"] = int(variant_id)
                except (ValueError, TypeError):
                    _logger.warning(
                        "Order %s: invalid variant ID '%s' for '%s' — using custom line.",
                        self.name, variant_id, line.product_id.display_name,
                    )
            line_items.append(item)

        if not line_items:
            raise UserError(_("No valid sale order lines to export for %s.") % self.name)

        # ── 4. Build payload ──────────────────────────────────────────────────
        if not partner.shopify_customer_id:
            raise UserError(
                _("Customer '%s' has no Shopify ID. Export the customer first.") % partner.name
            )
        try:
            shopify_customer_id_int = int(partner.shopify_customer_id)
        except (ValueError, TypeError):
            raise UserError(
                _("Customer '%s' has an invalid Shopify Customer ID: '%s'.")
                % (partner.name, partner.shopify_customer_id)
            )

        order_data = {
            "order": {
                "name":                self.name,
                "email":               partner.email or "",
                "customer":            {"id": shopify_customer_id_int},
                "line_items":          line_items,
                "billing_address":     self._shopify_address(self.partner_invoice_id),
                "shipping_address":    self._shopify_address(self.partner_shipping_id),
                "financial_status":    "paid" if self.invoice_status == 'invoiced' else "pending",
                "fulfillment_status":  None,
                "currency":            self.currency_id.name,
                "total_tax":           str(self.amount_tax),
                "note":                self.note or "",
                "tags":                "Exported from Odoo",
                "inventory_behaviour": "decrement_ignoring_policy",
            }
        }
        if self.amount_tax:
            order_data["order"]["tax_lines"] = [
                {"price": str(self.amount_tax), "title": "Tax", "rate": 0.0}
            ]

        # ── 5. Metafields ────────────────────────────────────────────────────
        metafields = self._build_order_metafields()
        if metafields:
            order_data['order']['metafields'] = metafields

        # ── 6. Send ───────────────────────────────────────────────────────────
        resp = session.post(
            f"https://{shop_url}/admin/api/{API}/orders.json",
            data=json.dumps(order_data),
            timeout=20,
        )
        _logger.info("Shopify order POST '%s' → %s", self.name, resp.status_code)

        if resp.status_code in (200, 201):
            data = resp.json().get('order', {})
            self.write({
                'shopify_order_id':      str(data.get('id', '')),
                'is_exported_to_shopify': True,
            })
        else:
            raise UserError(
                _("Shopify export failed for %s. Status %s:\n%s")
                % (self.name, resp.status_code, resp.text[:500])
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_order_metafields(self):
        self.ensure_one()
        metafields = []

        # Single line text fields
        text_fields = {
            'fiscal_position':   self.fiscal_position_id.name,
            'source':            self.source_id.name,
            'medium':            self.medium_id.name,
            'campaign':          self.campaign_id.name,
            'opportunity':       self.opportunity_id.name,
            'source_document':   self.client_order_ref or '',
            'shipping_policy':   self.picking_policy or '',
            'incoterm_location': self.incoterm_location or '',
            'incoterm':          self.incoterm.name,
            'exemption_code':    self.exemption_code_id.code or '',
            'exemption_number':  self.exemption_code or '',
            'pricelist':         self.pricelist_id.name,
            'sales_team':        self.team_id.name,
            'sales_person':      self.user_id.name,
            'customer_number':   self.partner_id.ref or '',
            'sales_agent':       self.sales_agent.name if self.sales_agent else '',
        }
        for key, value in text_fields.items():
            if value:
                metafields.append({
                    'namespace': 'custom',
                    'key':       key,
                    'value':     str(value),
                    'type':      'single_line_text_field',
                })

        # Delivery date — date_time type required by Shopify definition
        if self.commitment_date:
            metafields.append({
                'namespace': 'custom',
                'key':       'delivery_date',
                'value':     self.commitment_date.isoformat(),
                'type':      'date_time',
            })

        # Odoo order ID (integer)
        metafields.append({
            'namespace': 'custom',
            'key':       'order_id',
            'value':     str(self.id),
            'type':      'number_integer',
        })

        # Boolean metafields
        bool_fields = {
            'po':             self.po_processed,
            'processed':      self.processed,
            'payment_status': self.pay_processed,
        }
        for key, value in bool_fields.items():
            metafields.append({
                'namespace': 'custom',
                'key':       key,
                'value':     'true' if value else 'false',
                'type':      'boolean',
            })

        return metafields

    def _shopify_address(self, partner):
        name = partner.name or ""
        parts = name.split(' ', 1)
        first, last = parts[0], (parts[1] if len(parts) > 1 else "")
        raw_phone = partner.phone or partner.mobile or ""
        digits = re.sub(r'[^\d]', '', raw_phone)
        if digits and raw_phone.strip().startswith('+'):
            phone = '+' + digits
        elif digits and partner.country_id and partner.country_id.phone_code:
            phone = f"+{partner.country_id.phone_code}{digits}"
        else:
            phone = digits
        return {
            "first_name": first,
            "last_name":  last,
            "address1":   partner.street or "",
            "address2":   partner.street2 or "",
            "city":       partner.city or "",
            "province":   partner.state_id.name if partner.state_id else "",
            "country":    partner.country_id.name if partner.country_id else "",
            "zip":        partner.zip or "",
            "phone":      phone,
        }

    def _resolve_instance(self):
        if self.shopify_instance_id:
            return self.shopify_instance_id
        instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
        if len(instances) == 1:
            self.shopify_instance_id = instances[0].id
            return instances[0]
        raise UserError(_("Please select a Shopify Instance for order: %s") % self.name)

    @staticmethod
    def _make_session(instance):
        s = requests.Session()
        s.headers.update({
            "X-Shopify-Access-Token": instance.access_token,
            "Content-Type": "application/json",
        })
        return s
