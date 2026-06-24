from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import time

class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    shopify_collection_id = fields.Char(string='Shopify Collection ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)

    def _shopify_request(self, method, url, headers, data=None, retries=3):
        """Makes a Shopify API request with rate limit handling (429 retry)."""
        for attempt in range(retries):
            try:
                if method == 'GET':
                    response = requests.get(url, headers=headers, timeout=15)
                elif method == 'POST':
                    response = requests.post(url, headers=headers, data=data, timeout=15)
                elif method == 'PUT':
                    response = requests.put(url, headers=headers, data=data, timeout=15)

                if response.status_code == 429:
                    # Rate limited — wait and retry
                    wait = int(response.headers.get('Retry-After', 2)) + 1
                    time.sleep(wait)
                    continue

                # Stay under 2 calls/sec after every successful request
                time.sleep(0.6)
                return response

            except Exception as e:
                if attempt == retries - 1:
                    raise
                time.sleep(1)

        return response

    def action_export_to_shopify(self):
        """
        Exports the Odoo eCommerce category as a Shopify Smart Collection.
        Matches products by their Tag (derived from Odoo Category Hierarchy).
        """
        success_count = 0
        error_count = 0
        error_messages = []
        # Tracks name → shopify_collection_id for categories processed in this run
        seen_names = {}

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

            # 2. Skip categories whose name contains " /" (space + slash) — these are hierarchy labels
            category_name = (category.name or "").strip()
            if ' /' in category_name:
                continue

            # 3. Odoo duplicate check — same name already processed in this run
            if category_name in seen_names:
                # Link this duplicate to the already-exported collection and skip
                category.shopify_collection_id = seen_names[category_name]
                category.is_exported_to_shopify = True
                continue

            shop_url = instance.shop_url.replace('https://', '').replace('http://', '').strip('/')
            headers = {
                "X-Shopify-Access-Token": instance.access_token,
                "Content-Type": "application/json"
            }

            collection_data = {
                "smart_collection": {
                    "title": category_name,
                    "rules": [
                        {
                            "column": "tag",
                            "relation": "equals",
                            "condition": category_name
                        }
                    ],
                    "published_scope": "global"
                }
            }

            try:
                # 4. Determine if collection already exists on Shopify
                shopify_id = str(category.shopify_collection_id or "").split("/")[-1]
                shop_shopify_id = False

                if not shopify_id:
                    # Search Shopify for existing collection with same name
                    search_url = f"https://{shop_url}/admin/api/2024-01/smart_collections.json?title={category_name}"
                    s_res = self._shopify_request('GET', search_url, headers)
                    if s_res.status_code == 200:
                        s_data = s_res.json().get('smart_collections', [])
                        # Exact title match (Shopify search can return partial matches)
                        matched = [c for c in s_data if c.get('title', '').strip().lower() == category_name.lower()]
                        if matched:
                            shop_shopify_id = matched[0].get('id')
                    elif s_res.status_code != 404:
                        # Search itself failed — skip to avoid creating duplicate
                        error_count += 1
                        error_messages.append(
                            _("%s: Could not verify duplicates (search returned %s), skipping.") % (
                                category.name, s_res.status_code))
                        continue

                # 5. Create or Update
                if shopify_id or shop_shopify_id:
                    target_id = shopify_id or shop_shopify_id
                    url = f"https://{shop_url}/admin/api/2024-01/smart_collections/{target_id}.json"
                    response = self._shopify_request('PUT', url, headers, json.dumps(collection_data))

                    if response.status_code == 404:
                        # Collection deleted on Shopify side — recreate
                        url = f"https://{shop_url}/admin/api/2024-01/smart_collections.json"
                        response = self._shopify_request('POST', url, headers, json.dumps(collection_data))
                else:
                    url = f"https://{shop_url}/admin/api/2024-01/smart_collections.json"
                    response = self._shopify_request('POST', url, headers, json.dumps(collection_data))

                # 6. Result Handling
                if response.status_code in [200, 201]:
                    res_data = response.json()
                    exported_id = res_data.get("smart_collection", {}).get("id")
                    category.shopify_collection_id = exported_id
                    category.is_exported_to_shopify = True
                    seen_names[category_name] = exported_id
                    success_count += 1
                else:
                    error_count += 1
                    error_messages.append(
                        _("%s: Shopify Error (%s): %s") % (category.name, response.status_code, response.text))

            except Exception as e:
                error_count += 1
                error_messages.append(_("%s: Connection Error: %s") % (category.name, str(e)))

        # 5. UX Feedback
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
