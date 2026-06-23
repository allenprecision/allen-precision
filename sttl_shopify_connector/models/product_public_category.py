from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json

class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    shopify_collection_id = fields.Char(string='Shopify Collection ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)

    def action_export_to_shopify(self):
        """
        Exports the Odoo eCommerce category as a Shopify Smart Collection.
        Matches products by their Tag (derived from Odoo Category Hierarchy).
        """
        success_count = 0
        error_count = 0
        error_messages = []

        for category in self:
            # 1. Fallback Instance Logic
            instance = category.shopify_instance_id
            if not instance:
                instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
                if len(instances) == 1:
                    category.shopify_instance_id = instances[0].id
                    instance = category.shopify_instance_id
                else:
                    error_count += 1
                    error_messages.append(_("%s: Please select a Shopify Instance first.") % category.name)
                    continue

            shop_url = instance.shop_url.replace('https://', '').replace('http://', '').strip('/')
            headers = {
                "X-Shopify-Access-Token": instance.access_token,
                "Content-Type": "application/json"
            }

            # 2. MATCHING LOGIC
            # Note: product_template.py exports categories as tags split by '/'.
            # So "Electronics / Computers" results in tags "Electronics" and "Computers".
            # We match on the category's leaf name for simple rules.
            collection_data = {
                "smart_collection": {
                    "title": category.name,
                    "rules": [
                        {
                            "column": "tag",
                            "relation": "equals",
                            "condition": category.name
                        }
                    ],
                    "published_scope": "global"
                }
            }

            try:
                # 3. API CALL
                shopify_id = str(category.shopify_collection_id or "").split("/")[-1]
                shop_shopify_id = False
                if not shopify_id:
                    # Duplicate Detection: Search Shopify for a collection with this name
                    search_url = f"https://{shop_url}/admin/api/2024-01/smart_collections.json?title={category.name}"
                    try:
                        s_res = requests.get(search_url, headers=headers, timeout=15)
                        if s_res.status_code == 200:
                            s_data = s_res.json().get('smart_collections', [])
                            if s_data:
                                shop_shopify_id = s_data[0].get('id')
                    except:
                        pass

                if shopify_id or shop_shopify_id:
                    # Update existing
                    target_id = shopify_id or shop_shopify_id
                    url = f"https://{shop_url}/admin/api/2024-01/smart_collections/{target_id}.json"
                    response = requests.put(url, headers=headers, data=json.dumps(collection_data), timeout=15)
                    
                    if response.status_code == 404:
                         # Recreate if missing
                         url = f"https://{shop_url}/admin/api/2024-01/smart_collections.json"
                         response = requests.post(url, headers=headers, data=json.dumps(collection_data), timeout=15)
                else:
                    # Create new
                    url = f"https://{shop_url}/admin/api/2024-01/smart_collections.json"
                    response = requests.post(url, headers=headers, data=json.dumps(collection_data), timeout=15)

                # 4. RESULT HANDLING
                if response.status_code in [200, 201]:
                    res_data = response.json()
                    category.shopify_collection_id = res_data.get("smart_collection", {}).get("id")
                    category.is_exported_to_shopify = True
                    success_count += 1
                else:
                    error_count += 1
                    error_messages.append(_("%s: Shopify Error (%s): %s") % (category.name, response.status_code, response.text))

            except Exception as e:
                error_count += 1
                error_messages.append(_("%s: Connection Error: %s") % (category.name, str(e)))

        # 5. UX FEEDBACK
        message = _("%s collections successfully exported.") % success_count
        if error_count > 0:
            message += _("\n%s collections failed. Errors: %s") % (error_count, "; ".join(error_messages[:5]))

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
