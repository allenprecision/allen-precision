from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopify_order_id = fields.Char(string='Shopify Order ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)

    def action_export_to_shopify(self):
        success_count = 0
        error_count = 0
        error_messages = []
        success_orders = []
        existing_orders = []

        for order in self:
            try:
                order._export_to_shopify()
                success_count += 1
                success_orders.append(order.name)
            except Exception as e:
                error_count += 1
                if str(e) == "already exists in Shopify":
                    existing_orders.append(order.name)
                else:
                    error_messages.append(f"{order.name}: {str(e)}")

        message_parts = []

        if success_count > 0:
            message_parts.append(
                _("Orders exported successfully: %s") % ", ".join(success_orders[:10])
            )

        if existing_orders:
            if len(existing_orders) == 1:
                message_parts.append(
                    _("This order already exists in Shopify:\n%s") % existing_orders[0]
                )
            else:
                message_parts.append(
                    _("These %s orders already exist in Shopify:\n%s") % (
                        len(existing_orders),
                        "\n".join(existing_orders)
                    )
                )

        if error_messages:
            message_parts.append("\n".join(error_messages[:5]))

        message = "\n\n".join(message_parts)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Sync Results'),
                'message': message,
                'type': 'success' if error_count == 0 else 'warning',
                'sticky': error_count > 0,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically export related products to Shopify if possible."""
        orders = super(SaleOrder, self).create(vals_list)
        for order in orders:
            try:
                # We skip if no lines or if it's already being handled by a sync process
                if order.order_line:
                    order._sync_related_products_to_shopify()
            except Exception as e:
                _logger.error("Auto-sync of products failed for order %s: %s", order.name, str(e))
        return orders

    def _sync_related_products_to_shopify(self):
        """Helper to sync all products in this order to Shopify."""
        # Find default instance if not set
        instance = self.shopify_instance_id
        if not instance:
            instance = self.env['shopify.instance'].search([('state', '=', 'confirmed')], limit=1)
        
        if not instance:
            return
            
        # Get unique templates to avoid redundant API calls
        templates = self.order_line.mapped('product_id.product_tmpl_id')
        for template in templates:
            if not template.shopify_instance_id:
                template.shopify_instance_id = instance.id
            try:
                template._export_to_shopify()
            except Exception as e:
                _logger.warning("Failed to auto-export product %s: %s", template.name, str(e))

    def _export_to_shopify(self):
        _logger.warning("Shopify order export triggered for %s", self.name)
        self.ensure_one()

        if not self.shopify_instance_id:
            instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
            if len(instances) == 1:
                self.shopify_instance_id = instances[0].id
            else:
                raise UserError(_("Please select a Shopify Instance first for order: %s") % self.name)
        
        # 1. ENSURE CUSTOMER EXISTS ON SHOPIFY
        if not self.partner_id.shopify_customer_id:
            try:
                if not self.partner_id.shopify_instance_id:
                    self.partner_id.shopify_instance_id = self.shopify_instance_id.id
                self.partner_id._export_to_shopify()
            except Exception as e:
                raise UserError(_("Auto-export of customer %s failed: %s") % (self.partner_id.name, str(e)))
        
        # 2. ENSURE ALL PRODUCTS ARE SYNCED/UPDATED
        self._sync_related_products_to_shopify()

        instance = self.shopify_instance_id
        shop_url = (instance.shop_url or "").replace('https://', '').replace('http://', '').strip('/')

        url = f"https://{shop_url}/admin/api/2024-01/orders.json"

        headers = {
            "X-Shopify-Access-Token": instance.access_token,
            "Content-Type": "application/json"
        }
        # -----------------------------------------
        # CHECK EXISTING SHOPIFY ORDER BEFORE CREATE
        # -----------------------------------------
        if self.shopify_order_id:
            check_url = f"https://{shop_url}/admin/api/2024-01/orders/{self.shopify_order_id}.json"
            check_response = requests.get(check_url, headers=headers, timeout=20)

            if check_response.status_code == 200:
                raise UserError(_("already exists in Shopify"))
            elif check_response.status_code == 404:
                _logger.warning(
                    "Shopify order ID %s not found in Shopify. Recreating order for %s.",
                    self.shopify_order_id, self.name
                )
                self.shopify_order_id = False
                self.is_exported_to_shopify = False
            else:
                raise UserError(
                    _("Failed to verify existing Shopify order for %s. Status: %s. Response: %s")
                    % (self.name, check_response.status_code, check_response.text)
                )

        line_items = []
        for line in self.order_line:
            if line.display_type:
                continue

            if not line.product_id:
                continue

            # Double check variant sync (v_id should be populated now)
            if not line.product_id.shopify_variant_id:
                # Invalidate cache just in case
                line.product_id.invalidate_recordset(['shopify_variant_id'])
                if not line.product_id.shopify_variant_id:
                     raise UserError(_("Product '%s' could not be synced to Shopify. Variant ID missing.") % line.product_id.display_name)

            line_items.append({
                "variant_id": int(line.product_id.shopify_variant_id),
                "quantity": int(line.product_uom_qty),
                "price": str(line.price_unit),
                "title": line.name or line.product_id.display_name,
            })

        if not line_items:
            raise UserError(_("No valid sale order lines found to export."))

        billing_address = {
            "first_name": self.partner_invoice_id.name.split(' ', 1)[0] if self.partner_invoice_id.name else "",
            "last_name": self.partner_invoice_id.name.split(' ', 1)[1] if self.partner_invoice_id.name and ' ' in self.partner_invoice_id.name else "",
            "address1": self.partner_invoice_id.street or "",
            "address2": self.partner_invoice_id.street2 or "",
            "city": self.partner_invoice_id.city or "",
            "province": self.partner_invoice_id.state_id.name if self.partner_invoice_id.state_id else "",
            "country": self.partner_invoice_id.country_id.name if self.partner_invoice_id.country_id else "",
            "zip": self.partner_invoice_id.zip or "",
            "phone": self.partner_invoice_id.phone or self.partner_invoice_id.mobile or "",
        }

        shipping_address = {
            "first_name": self.partner_shipping_id.name.split(' ', 1)[0] if self.partner_shipping_id.name else "",
            "last_name": self.partner_shipping_id.name.split(' ', 1)[1] if self.partner_shipping_id.name and ' ' in self.partner_shipping_id.name else "",
            "address1": self.partner_shipping_id.street or "",
            "address2": self.partner_shipping_id.street2 or "",
            "city": self.partner_shipping_id.city or "",
            "province": self.partner_shipping_id.state_id.name if self.partner_shipping_id.state_id else "",
            "country": self.partner_shipping_id.country_id.name if self.partner_shipping_id.country_id else "",
            "zip": self.partner_shipping_id.zip or "",
            "phone": self.partner_shipping_id.phone or self.partner_shipping_id.mobile or "",
        }

        tax_lines = []
        if self.amount_tax:
            tax_lines.append({
                "price": str(self.amount_tax),
                "title": "Tax",
                "rate": 0.0
            })

        order_data = {
            "order": {
                "name": self.name,
                "email": self.partner_id.email or "",
                "customer": {
                    "id": int(self.partner_id.shopify_customer_id)
                },
                "line_items": line_items,
                "billing_address": billing_address,
                "shipping_address": shipping_address,
                "financial_status": "paid" if self.invoice_status == 'invoiced' else "pending",
                "fulfillment_status": None,
                "currency": self.currency_id.name,
                "total_tax": str(self.amount_tax),
                "note": self.note or "",
                "tags": "Exported from Odoo",
                "inventory_behaviour": "decrement_ignoring_policy",
            }
        }

        if tax_lines:
            order_data["order"]["tax_lines"] = tax_lines

        response = requests.post(url, headers=headers, data=json.dumps(order_data), timeout=20)

        if response.status_code in [200, 201]:
            res_data = response.json()
            self.shopify_order_id = res_data.get('order', {}).get('id')
            self.is_exported_to_shopify = True
        else:
            raise UserError(
                _("Shopify Export Failed for %s. Status: %s. Response: %s")
                % (self.name, response.status_code, response.text)
            )