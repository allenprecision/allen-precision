from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json

class ShopifyInstance(models.Model):
    _name = 'shopify.instance'
    _description = 'Shopify Instance'

    name = fields.Char(string='Name', required=True)
    shop_url = fields.Char(string='Shop URL', required=True, help="e.g. your-store.myshopify.com")
    access_token = fields.Char(string='API Access Token', required=True, help="Shopify Admin API Access Token")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('error', 'Error')
    ], string='Status', default='draft')
    location_id = fields.Char(string='Shopify Location ID', help="Required for Stock Synchronization. Get this from Shopify Settings > Locations.")

    def action_test_connection(self):
        for record in self:
            # Clean URL: Remove http://, https:// and trailing slashes
            shop_url = record.shop_url or ""
            shop_url = shop_url.replace('https://', '').replace('http://', '').strip('/')
            
            url = f"https://{shop_url}/admin/api/2024-01/shop.json"
            headers = {
                "X-Shopify-Access-Token": record.access_token,
                "Content-Type": "application/json"
            }
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    record.state = 'confirmed'
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Success'),
                            'message': _('Connection successful with Shopify store: %s') % response.json().get('shop', {}).get('name'),
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    record.state = 'error'
                    raise UserError(_("Connection failed. Status Code: %s\nResponse: %s") % (response.status_code, response.text))
            except Exception as e:
                record.state = 'error'
                raise UserError(_("Connection Error: %s") % str(e))

    def action_apply_to_all_products(self):
        """Set this instance on all product templates and partners that don't have one."""
        self.ensure_one()
        # Products
        products = self.env['product.template'].search([('shopify_instance_id', '=', False)])
        products.write({'shopify_instance_id': self.id})
        # Customers
        partners = self.env['res.partner'].search([('shopify_instance_id', '=', False), ('customer_rank', '>', 0)])
        partners.write({'shopify_instance_id': self.id})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Case Instance applied to %s products and %s customers.') % (len(products), len(partners)),
                'type': 'success',
                'sticky': False,
            }
        }
