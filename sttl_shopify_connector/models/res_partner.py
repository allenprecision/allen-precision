from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json

class ResPartner(models.Model):
    _inherit = 'res.partner'

    shopify_customer_id = fields.Char(string='Shopify Customer ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)

    def action_export_to_shopify(self):
        # Support bulk export
        success_count = 0
        error_count = 0
        error_messages = []

        for partner in self:
            try:
                partner._export_to_shopify()
                success_count += 1
            except Exception as e:
                error_count += 1
                # error_messages.append(f"{partner.name}: {str(e)}")
                simple_error = partner._get_simple_shopify_error(e)
                error_messages.append(f"{partner.name}: {simple_error}")

        message = _("%s customers exported successfully.") % success_count
        if error_count > 0:
            # message += _("\n%s customers failed. Errors: %s") % (error_count, "; ".join(error_messages[:5]))
            message += _("\n%s customers failed.") % error_count
            message += _("\nErrors: %s") % "; ".join(error_messages[:5])

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

    def _export_to_shopify(self):
        """Internal method to export a single customer to Shopify."""
        if not self.shopify_instance_id:
            # Smart logic: if only one instance exists, use it automatically
            instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
            if len(instances) == 1:
                self.shopify_instance_id = instances[0].id
            else:
                raise UserError(_("Please select a Shopify Instance first for customer: %s") % self.name)
        
        instance = self.shopify_instance_id
        shop_url = instance.shop_url or ""
        shop_url = shop_url.replace('https://', '').replace('http://', '').strip('/')
        headers = {
            "X-Shopify-Access-Token": instance.access_token,
            "Content-Type": "application/json"
        }
        # Verify Shopify customer still exists
        if self.shopify_customer_id:
            check_url = f"https://{shop_url}/admin/api/2024-01/customers/{self.shopify_customer_id}.json"
            check = requests.get(check_url, headers=headers, timeout=10)

            if check.status_code == 404:
                # Customer removed from Shopify
                self.shopify_customer_id = False

        url = f"https://{shop_url}/admin/api/2024-01/customers.json"
        if self.shopify_customer_id:
            url = f"https://{shop_url}/admin/api/2024-01/customers/{self.shopify_customer_id}.json"

        

        names = self.name.split(' ')
        first_name = ' '.join(names[:-1])
        last_name = names[-1] if len(names) > 1 else ""
        phone = self.phone or self.mobile or ""

        customer_data = {
            "customer": {
                "first_name": first_name,
                "last_name": last_name,
                "email": self.email or "",
                "phone": phone,
                "addresses": [
                    {
                        "address1": self.street or "",
                        "address2": self.street2 or "",
                        "city": self.city or "",
                        "province": self.state_id.name if self.state_id else "",
                        "phone": phone,
                        "zip": self.zip or "",
                        "last_name": last_name,
                        "first_name": first_name,
                        "country": self.country_id.name if self.country_id else ""
                    }
                ]
            }
        }

        # Handle custom metafields based on user requirements
        metafields = []
        custom_fields_mapping = {
            'customer_number': 'ref',
            'contact_type': 'contact_type',
            'contact_1': 'contact_1',
            'contact_2': 'contact_2',
        }

        for shopify_key, odoo_field in custom_fields_mapping.items():
            if hasattr(self, odoo_field) and getattr(self, odoo_field):
                val = getattr(self, odoo_field)
                
                field_def = self._fields.get(odoo_field)
                if field_def:
                    if field_def.type == 'many2one':
                        val = val.display_name or val.name
                    elif field_def.type == 'selection':
                        # Try to get the string representation of the selection
                        selection_dict = dict(field_def._description_selection(self.env))
                        val = selection_dict.get(val, val)

                if val:
                    metafields.append({
                        "namespace": "custom",
                        "key": shopify_key,
                        "value": str(val),
                        "type": "single_line_text_field"
                    })

        if metafields:
            customer_data["customer"]["metafields"] = metafields

        if self.shopify_customer_id:
            response = requests.put(url, headers=headers, data=json.dumps(customer_data), timeout=15)
        else:
            response = requests.post(url, headers=headers, data=json.dumps(customer_data), timeout=15)

        if response.status_code in [200, 201]:
            res_data = response.json()
            self.shopify_customer_id = res_data.get('customer', {}).get('id')
            self.is_exported_to_shopify = True
        elif response.status_code == 422 and 'phone' in response.text:
            # RETRY WITHOUT PHONE: Shopify is very strict about phone formats
            customer_data["customer"].pop("phone", None)
            if "addresses" in customer_data["customer"]:
                for addr in customer_data["customer"]["addresses"]:
                    addr.pop("phone", None)
            
            if self.shopify_customer_id:
                response = requests.put(url, headers=headers, data=json.dumps(customer_data), timeout=15)
            else:
                response = requests.post(url, headers=headers, data=json.dumps(customer_data), timeout=15)
            
            if response.status_code in [200, 201]:
                res_data = response.json()
                self.shopify_customer_id = res_data.get('customer', {}).get('id')
                self.is_exported_to_shopify = True
            else:
                raise UserError(_("Shopify Export Failed for %s. Status: %s. Response: %s") % (self.name, response.status_code, response.text))
        else:
            raise UserError(_("Shopify Export Failed for %s. Status: %s. Response: %s") % (self.name, response.status_code, response.text))

    def _shopify_customer_exists(self, shop_url, headers):
        if not self.shopify_customer_id:
            return False

        url = f"https://{shop_url}/admin/api/2024-01/customers/{self.shopify_customer_id}.json"
        response = requests.get(url, headers=headers, timeout=10)

        return response.status_code == 200
    
    def _get_simple_shopify_error(self, error):
        error_text = str(error)

        if 'phone' in error_text and 'is invalid' in error_text:
            return _("Invalid phone number")

        if 'email' in error_text and 'has already been taken' in error_text:
            return _("Email already exists in Shopify")

        if 'Status: 404' in error_text:
            return _("Customer not found in Shopify")

        if 'Status: 401' in error_text or 'Status: 403' in error_text:
            return _("Shopify connection failed. Please check access token.")

        if 'Please select a Shopify Instance first' in error_text:
            return _("Shopify instance is missing")

        return _("Export failed. Please check customer data.")