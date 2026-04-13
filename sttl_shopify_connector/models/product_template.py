from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import base64
import re
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    shopify_product_id = fields.Char(string='Shopify Product ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)

    def action_export_to_shopify(self):
        # Support bulk export
        success_count = 0
        error_count = 0
        error_messages = []

        for product in self:
            try:
                product._export_to_shopify()
                success_count += 1
            except Exception as e:
                error_count += 1
                error_messages.append(f"{product.name}: {str(e)}")

        message = _("%s products exported successfully.") % success_count
        if error_count > 0:
            message += _("\n%s products failed. Errors: %s") % (error_count, "; ".join(error_messages[:5]))
        _logger.info("EXPORT RESULT: %s", message)
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
        """Internal method to export a single product to Shopify."""
        if not self.shopify_instance_id:
            instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
            if len(instances) == 1:
                self.shopify_instance_id = instances[0].id
            else:
                raise UserError(_("Please select a Shopify Instance first for product: %s") % self.name)

        instance = self.shopify_instance_id

        shop_url = instance.shop_url or ""
        shop_url = shop_url.replace('https://', '').replace('http://', '').strip('/')

        headers = {
            "X-Shopify-Access-Token": instance.access_token,
            "Content-Type": "application/json"
        }
        spec_plain = ""
        spec_list = []
        spec_dict = {}
        if self.attribute_line_ids:
            for line in self.attribute_line_ids:
                # Key for individual metafield mapping
                attr_key = line.attribute_id.name.lower().replace(" ", "_")
                val_names = line.value_ids.mapped('name')
                spec_dict[attr_key] = val_names

                # Dynamic Label Format: "Attribute Name: Value1 or Value2"
                attr_label = line.attribute_id.name
                attr_values = " or ".join(val_names)
                spec_list.append(f"{attr_label}: {attr_values}")
                        
                # Plain Text format with Newlines (for Multi-line Metafield)
                spec_plain += f"{attr_label}: {attr_values}\n"
        
        # -------- SHORT DESCRIPTION --------
        description_html = (
            getattr(self, 'description_ecommerce', '')
            or getattr(self, 'website_description', '')
            or self.description_sale
            or self.name
            or ""
        ).strip()
        
        short_description = ""
        if description_html:
            clean_text = re.sub('<[^<]+?>', '', description_html)
            clean_text = ' '.join(clean_text.split())
        
            limit = 1000
            if len(clean_text) > limit:
                short_description = ""
                for idx, char in enumerate(clean_text):
                    if idx < limit:
                        short_description += char
                short_description += "..."
            else:
                short_description = clean_text
        
        # -------- BODY HTML --------
        body_html = description_html or ""
        
        # -------- LONG DESCRIPTION SPLIT --------
        long_description = getattr(self, 'product_tab_description', '') or ""
        
        # Get base URL for absolute image paths
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        tab_images_to_upload = []
        if long_description:
            # 1. Extract regular Odoo images (/web/image/...) and upload them as actual Shopify assets
            # This is the most reliable way for Odoo.sh
            odoo_img_matches = re.findall(r'src=["\'](\/web\/image\/([^?^"^\']+))["\']', long_description)
            for i, (path, img_id) in enumerate(odoo_img_matches):
                # We can fetch the image content directly from Odoo database if we have the ID/Path
                # or use a placeholder for now to upload it as a product image.
                # Let's try to get binary from Odoo.
                try:
                    # Try finding the attachment via ID in path
                    match_id = re.search(r'\/(\d+)\-', path)
                    if match_id:
                        attachment = self.env['ir.attachment'].sudo().browse(int(match_id.group(1)))
                        if attachment.exists() and attachment.datas:
                            tab_images_to_upload.append({
                                "attachment": attachment.datas.decode('utf-8'),
                                "filename": f"desc_img_{self.id}_{i}.jpg"
                            })
                except:
                    pass

            # 2. Extract Base64 images and upload as actual Shopify assets
            b64_matches = re.findall(r'src=["\'](data:image\/([^;]+);base64,([^"\']+))["\']', long_description)
            for i, (full_src, fmt, b64_data) in enumerate(b64_matches):
                filename = f"tab_img_{self.id}_{i}.{fmt}"
                tab_images_to_upload.append({
                    "attachment": b64_data,
                    "filename": filename
                })
                # Remove the giant string to keep payload small
                long_description = long_description.replace(full_src, f"#IMAGE_DESC_{i+1}#")

            # Clean up whitespace
            long_description = re.sub(r'\s+', ' ', long_description)

        # Clean up empty tags
        long_description = re.sub(r'<p>\s*</p>', '', long_description, flags=re.IGNORECASE)
        long_description = re.sub(r'<div>\s*</div>', '', long_description, flags=re.IGNORECASE)
        
        MAX = 60000
        parts = [long_description[i:i+MAX] for i in range(0, len(long_description), MAX)]
        
        # -------- TAGS & CATEGORY --------
        tags_list = []
        # Removed categ_id export as tags per user request
        
        # Explicitly map Odoo Public Categories (eCommerce Categories) as Shopify Tags
        if hasattr(self, 'public_categ_ids') and self.public_categ_ids:
            for cat in self.public_categ_ids:
                if cat.name:
                    tags_list.append(cat.display_name)
        
        if hasattr(self, 'product_tag_ids') and self.product_tag_ids:
            tags_list.extend(self.product_tag_ids.mapped('name'))
        
        # Clean and unique tags
        final_tags = set()
        for t in tags_list:
            if t:
                # Only split if there are spaces around the slash (Odoo hierarchy pattern)
                # This ensures "Brands / Sitepro" splits, but "Brands/Sitepro" stays single.
                if ' / ' in t:
                    final_tags.update([part.strip() for part in t.split(' / ')])
                else:
                    final_tags.add(t.strip())
        
        tags_str = ", ".join(sorted(list(final_tags)))

        # -------- METAFIELDS --------
        metafields = []
        
        # Odoo Metadata
        metafields.append({"namespace": "odoo", "key": "id", "value": str(self.id), "type": "single_line_text_field"})
        
        # Descriptions & Tabs
        if short_description:
            metafields.append({"namespace": "custom", "key": "short_info", "value": short_description, "type": "single_line_text_field"})

        # Master Specification (Plain Text with Newlines for Multi-line Metafield)
        if spec_plain:
            metafields.append({
                "namespace": "custom", 
                "key": "product_specification", 
                "value": spec_plain, 
                "type": "multi_line_text_field"
            })

        # Brand / Manufacturer / Vendor
        vendor_name = "Odoo"
        if self.seller_ids:
            # Prioritize Odoo's Primary Vendor (Seller) as Shopify Vendor
            vendor_name = self.seller_ids[0].partner_id.name
        elif hasattr(self, 'product_brand_id') and self.product_brand_id:
            vendor_name = self.product_brand_id.name
        else:
            vendor_name = self.name # Fallback to product name if no vendor/brand
        
        # Add brand metafield for enhanced filtering
        brand_val = getattr(self, 'product_brand_id', False)
        if brand_val and hasattr(brand_val, 'name'):
            metafields.append({"namespace": "custom", "key": "brand", "value": brand_val.name, "type": "single_line_text_field"})

        # odoo_sku Metafield Logic:
        # 1. If multiple variants exist, HIDE odoo_sku from the main product page (it lives in variants).
        # 2. If single product (variants <= 1), display odoo_sku on the main product page.
        if len(self.product_variant_ids) <= 1:
            odoo_sku_val = self.default_code or getattr(self, 'odoo_sku', False)
            if odoo_sku_val:
                metafields.append({"namespace": "custom", "key": "odoo_sku", "value": str(odoo_sku_val), "type": "single_line_text_field"})
        
        if self.barcode:
            metafields.append({"namespace": "custom", "key": "barcode", "value": str(self.barcode), "type": "single_line_text_field"})

        if self.weight:
            metafields.append({"namespace": "custom", "key": "weight", "value": str(self.weight), "type": "single_line_text_field"})

        if self.volume:
            metafields.append({"namespace": "custom", "key": "volume", "value": str(self.volume), "type": "single_line_text_field"})

        if self.hs_code:
            metafields.append({"namespace": "custom", "key": "hs_code", "value": str(self.hs_code), "type": "single_line_text_field"})

        # UOM
        if self.uom_id:
            metafields.append({"namespace": "custom", "key": "uom", "value": self.uom_id.name, "type": "single_line_text_field"})
            metafields.append({"namespace": "custom", "key": "uom_id", "value": self.uom_id.name, "type": "single_line_text_field"})
        
        if self.uom_po_id:
            metafields.append({"namespace": "custom", "key": "uom_po_id", "value": self.uom_po_id.name, "type": "single_line_text_field"})

        # Availability / Website Settings
        if hasattr(self, 'out_of_stock_message') and self.out_of_stock_message:
            metafields.append({"namespace": "custom", "key": "out_of_stock_message", "value": self.out_of_stock_message, "type": "single_line_text_field"})

        if hasattr(self, 'website_size_x') and self.website_size_x:
            metafields.append({"namespace": "custom", "key": "website_size_x", "value": str(self.website_size_x), "type": "single_line_text_field"})

        if hasattr(self, 'website_size_y') and self.website_size_y:
            metafields.append({"namespace": "custom", "key": "website_size_y", "value": str(self.website_size_y), "type": "single_line_text_field"})

        if hasattr(self, 'purchase_ok'):metafields.append({"namespace": "custom", "key": "purchase_ok", "value": "true" if self.purchase_ok else "false", "type": "single_line_text_field"})

        if hasattr(self, 'sale_ok'):metafields.append({"namespace": "custom", "key": "sale_ok", "value": "true" if self.sale_ok else "false", "type": "single_line_text_field"})

        if hasattr(self, 'show_availability'):
            metafields.append({"namespace": "custom", "key": "show_availability", "value": "true" if self.show_availability else "false", "type": "single_line_text_field"})

        # SEO Shorthand Variables
        seo_title = ""
        seo_description = ""

        # Mapping Odoo SEO to Shopify SEO (global namespace)
        if hasattr(self, 'website_meta_title') and self.website_meta_title:
             seo_title = self.website_meta_title
             metafields.append({"namespace": "global", "key": "title_tag", "value": str(seo_title), "type": "single_line_text_field"})
        if hasattr(self, 'website_meta_description') and self.website_meta_description:
             seo_description = self.website_meta_description
             metafields.append({"namespace": "global", "key": "description_tag", "value": str(seo_description), "type": "multi_line_text_field"})

        # -------- FINAL PAYLOAD --------
        product_data = {
            "product": {
                "title": self.name,
                "body_html": long_description or body_html,
                "vendor": vendor_name,
                # "product_type": self.categ_id.name if self.categ_id else "Default",
                "tags": tags_str,
                "status": "active" if self.sale_ok else "archived",
                "metafields": metafields,
            }
        }
        # Build variants payload
        # Build variants payload
        variants_payload, options_payload = self._shopify_build_variants_payload()
        if variants_payload:
            product_data["product"]["variants"] = variants_payload
            if options_payload:
                product_data["product"]["options"] = options_payload
        else:
            # Single product SKU: Map ES Product SKU as the Primary SKU
            # Check both possible custom field names
            sku = (
                getattr(self, 'es_product_sku', False) 
                or getattr(self, 'product_sku', False)
                or self.default_code 
                or ""
            )
            product_data["product"]["variants"] = [{
                "sku": sku or "",
                "price": str(self.list_price),
                "weight": self.weight if hasattr(self, 'weight') else 0.0,
                "barcode": self.barcode or "",
                # "inventory_management": "shopify" if self.detailed_type == 'product' else None,
                "taxable": True if self.taxes_id else False,
            }]

        # -----------------------------
        # FIX 1: MULTIPLE IMAGES EXPORT (Template + Variants)
        # -----------------------------
        images = []

        # Main image
        if self.image_1920:
            image_b64 = base64.b64encode(base64.b64decode(self.image_1920)).decode('utf-8')
            images.append({
                "attachment": image_b64,
                "filename": f"{self.name.replace(' ', '_')}_main.jpg"
            })

        # Template extra images
        if hasattr(self, 'product_template_image_ids'):
            for img in self.product_template_image_ids:
                if img.image_1920:
                    image_b64 = base64.b64encode(base64.b64decode(img.image_1920)).decode('utf-8')
                    images.append({
                        "attachment": image_b64,
                        "filename": f"{self.name.replace(' ', '_')}_{img.id}.jpg"
                    })

        # Variant specific images
        for variant in self.product_variant_ids:
            if variant.image_1920 and variant.image_1920 != self.image_1920:
                image_b64 = base64.b64encode(base64.b64decode(variant.image_1920)).decode('utf-8')
                filename = f"variant_{variant.id}.jpg"
                img_payload = {
                    "attachment": image_b64,
                    "filename": filename,
                    "alt": f"variant_{variant.id}",
                }
                if variant.shopify_variant_id:
                    img_payload["variant_ids"] = [int(variant.shopify_variant_id)]
                
                images.append(img_payload)

        if images:
            product_data["product"]["images"] = images
        
        # Add images extracted from the tab description
        if tab_images_to_upload:
            if "images" not in product_data["product"] or not isinstance(product_data["product"]["images"], list):
                product_data["product"]["images"] = []
            product_data["product"]["images"].extend(tab_images_to_upload)

        # -----------------------------
        # FIX 2: PREVENT DUPLICATES (SKU LOOKUP) & SAFE UPDATE
        # -----------------------------
        # Attempt to find by SKU if no ID is stored locally to prevent duplicates
        if not self.shopify_product_id:
            # Match by the Primary SKU source (ES Product SKU)
            sku_to_match = getattr(self, 'es_product_sku', self.default_code)
            if sku_to_match:
                # Search Shopify for product with this SKU in any variant
                search_url = f"https://{shop_url}/admin/api/2024-01/products.json?vendor={vendor_name}"
                try:
                    s_res = requests.get(search_url, headers=headers, timeout=15)
                    if s_res.status_code == 200:
                        products = s_res.json().get('products', [])
                        for p in products:
                            for v in p.get('variants', []):
                                if v.get('sku') == sku_to_match:
                                    self.shopify_product_id = str(p.get('id'))
                                    break
                            if self.shopify_product_id: break
                except:
                    pass

        if self.shopify_product_id:
            product_id = str(self.shopify_product_id).split("/")[-1]
            url = f"https://{shop_url}/admin/api/2024-01/products/{product_id}.json"
            response = requests.put(url, headers=headers, data=json.dumps(product_data), timeout=60)
            _logger.info("Shopify Export: PUT Update Response for %s: %s - %s", self.name, response.status_code, response.text)

            # If product not found in Shopify (deleted there), reset locally and recreate
            if response.status_code == 404:
                self.shopify_product_id = False
                url = f"https://{shop_url}/admin/api/2024-01/products.json"
                response = requests.post(url, headers=headers, data=json.dumps(product_data), timeout=60)
                _logger.info("Shopify Export: POST Re-create Response for %s: %s - %s", self.name, response.status_code, response.text)
        else:
            # Create new
            url = f"https://{shop_url}/admin/api/2024-01/products.json"
            response = requests.post(url, headers=headers, data=json.dumps(product_data), timeout=60)
            _logger.info("Shopify Export: POST Create Response for %s: %s - %s", self.name, response.status_code, response.text)

        # -----------------------------
        # RESPONSE HANDLING
        # -----------------------------
        if response.status_code in [200, 201]:
            res_data = response.json()
            shopify_product = res_data.get("product", {})
            self.shopify_product_id = shopify_product.get("id")
            self.is_exported_to_shopify = True
            if self.shopify_product_id:
                gql_url = f"https://{shop_url}/admin/api/2024-01/graphql.json"

                headers = {
                    "X-Shopify-Access-Token": instance.access_token,
                    "Content-Type": "application/json",
                }

                query = """
                mutation UpdateProductSEO($input: ProductUpdateInput!) {
                productUpdate(product: $input) {
                    product {
                    id
                    seo {
                        title
                        description
                    }
                    }
                    userErrors {
                    field
                    message
                    }
                }
                }
                """

                payload = {
                    "query": query,
                    "variables": {
                        "input": {
                            "id": f"gid://shopify/Product/{self.shopify_product_id}",
                            "seo": {
                                "title": self.website_meta_title or "",
                                "description": self.website_meta_description or ""
                            }
                        }
                    }
                }

                gql_response = requests.post(gql_url, headers=headers, json=payload, timeout=60)

                print("SEO Status:", gql_response.status_code)
                print("SEO Response:", gql_response.text)

                data = gql_response.json()

                if data.get("errors"):
                    print("GraphQL errors:", data["errors"])

                user_errors = (
                    data.get("data", {})
                        .get("productUpdate", {})
                        .get("userErrors", [])
                )

                if user_errors:
                    print("User errors:", user_errors)
                else:
                    print("SEO updated successfully")
            # SAVE VARIANT IDS AND SYNC STOCK
            shopify_variants = shopify_product.get("variants", [])
            location_id = instance.location_id
            for odoo_variant, shopify_variant in zip(self.product_variant_ids, shopify_variants):
                odoo_variant.shopify_variant_id = shopify_variant.get("id")
                inventory_item_id = shopify_variant.get("inventory_item_id")
                
                # Sync Stock if location_id is configured
                if location_id and inventory_item_id:
                    stock_qty = odoo_variant.qty_available
                    inventory_url = f"https://{shop_url}/admin/api/2024-01/inventory_levels/set.json"
                    inv_data = {
                        "location_id": int(location_id),
                        "inventory_item_id": int(inventory_item_id),
                        "available": int(stock_qty)
                    }
                    try:
                        requests.post(inventory_url, headers=headers, data=json.dumps(inv_data), timeout=15)
                    except:
                        pass

            # Link Variant Images
            shopify_images = shopify_product.get("images", [])
            variant_updates = []
            for odoo_variant in self.product_variant_ids:
                marker = f"variant_{odoo_variant.id}"
                matching_img = next((img for img in shopify_images if img.get('alt') == marker), None)
                if matching_img:
                    variant_updates.append({
                        "id": odoo_variant.shopify_variant_id,
                        "image_id": matching_img.get('id')
                    })
            
            # --- IMAGE URL REPLACEMENT PASS ---
            # Replace #IMAGE_DESC_N# placeholders in body_html with actual Shopify URLs
            updated_body_html = long_description or body_html
            desc_img_count = 1
            for img in shopify_images:
                # Based on the filename pattern used in the first pass
                if f"desc_img_{self.id}_" in img.get('src', '') or f"tab_img_{self.id}_" in img.get('src', ''):
                    marker = f"#IMAGE_DESC_{desc_img_count}#"
                    real_url = img.get('src')
                    if real_url:
                        updated_body_html = updated_body_html.replace(marker, real_url)
                    desc_img_count += 1
            
            if variant_updates or (desc_img_count > 1):
                update_url = f"https://{shop_url}/admin/api/2024-01/products/{self.shopify_product_id}.json"
                update_payload = {"product": {"id": self.shopify_product_id}}
                if variant_updates:
                    update_payload["product"]["variants"] = variant_updates
                if desc_img_count > 1:
                    update_payload["product"]["body_html"] = updated_body_html
                
                requests.put(update_url, headers=headers, data=json.dumps(update_payload), timeout=15)
        else:
            raise UserError(_("Shopify Export Failed for %s. Status: %s. Response: %s") % (
                self.name, response.status_code, response.text))
        
    def _shopify_build_variants_payload(self):
        """
        Build Shopify variants + options from Odoo variants with consistent ordering.
        Supports custom ES Product SKU fields.
        """
        self.ensure_one()
        variants_payload = []
        options_payload = []
        
        # 1. Define Options from Attribute Lines (Maintains ordering)
        attribute_lines = self.attribute_line_ids
        currency_symbol = self.currency_id.symbol or "$"
        _logger.info("Shopify Export: Starting variant payload build for product '%s' (ID: %s)", self.name, self.id)
        
        for line in attribute_lines:
            if not line.attribute_id.name:
                continue
                
            # Get actual values for this attribute line for the Shopify 'Option values' field
            # Use product_template_value_ids to capture the price_extra for this template
            line_values = []
            for ptav_template in line.product_template_value_ids:
                name = ptav_template.name
                if ptav_template.price_extra > 0:
                    name += f" + {currency_symbol} {ptav_template.price_extra:,.2f}"
                line_values.append(name)
            
            _logger.info("Shopify Export: Attribute '%s' found values: %s", line.attribute_id.name, line_values)
                
            if not line_values:
                line_values = ["Default"] # Absolute fallback if no values exist
                
            options_payload.append({
                "name": line.attribute_id.name,
                "values": line_values
            })

        # 2. Build Variants mapping to option1, option2, option3
        # Use child_attribute_line_ids or variant_ids to be safe in different Odoo versions
        odoo_variants = self.product_variant_ids
        
        # VIRTUAL VARIANT LOGIC:
        # If Odoo is set to "Never Create Variants", it only has 1 variant record.
        # We need to virtually generate the Shopify variants from the attribute lines.
        if len(odoo_variants) <= 1 and self.attribute_line_ids:
            import itertools
            _logger.info("Shopify Export: Generating virtual variants for 'Never' creation mode on %s", self.name)
            
            # Use ptav collections from lines for combinations
            all_ptav_lines = [line.product_template_value_ids for line in attribute_lines[:3]]
            all_combinations = list(itertools.product(*all_ptav_lines))
            
            for combo in all_combinations:
                extra_price = sum(v.price_extra for v in combo)
                sku_base = getattr(self, 'es_product_sku', self.default_code) or f"PROD-{self.id}"
                # Create a unique SKU for each virtual variant
                variant_sku = f"{sku_base}-" + "-".join([v.name[:3].upper() for v in combo])
                
                variant_dict = {
                    "sku": variant_sku,
                    "price": str(self.list_price + extra_price),
                    "weight": getattr(self, 'weight', 0.0),
                    "barcode": self.barcode or "",
                    "inventory_policy": "continue" if getattr(self, 'out_of_stock_action', False) == 'available' or getattr(self, 'allow_out_of_stock_order', False) else "deny",
                }
                
                # Map option names
                for i, ptav in enumerate(combo):
                    name = ptav.name
                    if ptav.price_extra > 0:
                        name += f" + {currency_symbol} {ptav.price_extra:,.2f}"
                    variant_dict[f"option{i+1}"] = name
                
                # Fill remaining options
                for i in range(len(combo), 3):
                    variant_dict[f"option{i+1}"] = None
                
                variants_payload.append(variant_dict)
                _logger.info("Shopify Export: Generated Virtual Variant: %s", variant_dict)
            
            return variants_payload, options_payload

        # STANDARD VARIANT LOGIC:
        _logger.info("Shopify Export: Found %s variants in Odoo for product %s", len(odoo_variants), self.name)
        
        for v in odoo_variants:
            # PRIMARY SKU: Map ES Product SKU (from variant or template) as the main Shopify SKU
            sku = (
                getattr(v, 'es_product_sku', False) 
                or getattr(self, 'es_product_sku', False)
                or getattr(v, 'product_sku', False)
                or getattr(self, 'product_sku', False)
                or v.default_code 
                or ""
            )

            variant_dict = {
                "sku": sku or "",
                "price": str(v.lst_price if hasattr(v, "lst_price") else self.list_price),
                "weight": v.weight if hasattr(v, 'weight') else getattr(self, 'weight', 0.0),
                "barcode": v.barcode or self.barcode or "",
                # "inventory_management": "shopify" if self.detailed_type == 'product' else None,
                "inventory_policy": "continue" if getattr(self, 'out_of_stock_action', False) == 'available' or getattr(self, 'allow_out_of_stock_order', False) else "deny",
            }
            
            # Include Shopify ID if it exists to ensure update instead of recreation
            if hasattr(v, 'shopify_variant_id') and v.shopify_variant_id:
                variant_dict["id"] = int(str(v.shopify_variant_id).split("/")[-1])
            
            # Sync custom metafields for variant
            v_metafields = []
            
            # 1. odoo_sku (Internal Reference)
            odoo_sku_variant = v.default_code or getattr(v, 'odoo_sku', False) or getattr(self, 'default_code', False)
            if odoo_sku_variant:
                v_metafields.append({"namespace": "custom", "key": "odoo_sku", "value": str(odoo_sku_variant), "type": "single_line_text_field"})

            # 2. weight
            weight_variant = v.weight if hasattr(v, 'weight') and v.weight else getattr(self, 'weight', False)
            if weight_variant:
                v_metafields.append({"namespace": "custom", "key": "weight", "value": str(weight_variant), "type": "single_line_text_field"})

            # 3. volume
            vol_v = v.volume if hasattr(v, 'volume') and v.volume else getattr(self, 'volume', False)
            if vol_v:
                v_metafields.append({"namespace": "custom", "key": "volume", "value": str(vol_v), "type": "single_line_text_field"})

            # 4. height
            h_v = getattr(v, 'height', False) or getattr(self, 'height', False)
            if h_v:
                v_metafields.append({"namespace": "custom", "key": "height", "value": str(h_v), "type": "single_line_text_field"})

            # 5. country_of_origin
            coo = getattr(v, 'country_of_origin', False) or getattr(self, 'country_of_origin', False)
            if coo:
                coo_val = coo.name if hasattr(coo, 'name') else str(coo)
                v_metafields.append({"namespace": "custom", "key": "country_of_origin", "value": coo_val, "type": "single_line_text_field"})

            # 6. bin_location_id
            bin_v = getattr(v, 'bin_location_id', False) or getattr(self, 'bin_location_id', False)
            if bin_v:
                v_metafields.append({"namespace": "custom", "key": "bin_location_id", "value": str(bin_v.name), "type": "single_line_text_field"})

            # 7. is_published
            pub_v = getattr(v, 'is_published', False) or getattr(self, 'is_published', False)
            if pub_v:
                v_metafields.append({"namespace": "custom", "key": "is_published", "value": str(pub_v), "type": "single_line_text_field"})

            # 8. variant_color_images
            vc_v = getattr(v, 'variant_color_images', False) or getattr(self, 'variant_color_images', False)
            if vc_v:
                v_metafields.append({"namespace": "custom", "key": "variant_color_images", "value": str(vc_v), "type": "single_line_text_field"})

            barcode_variant = v.barcode if hasattr(v, 'barcode') and v.barcode else getattr(self, 'barcode', False)
            if barcode_variant:
                v_metafields.append({"namespace": "custom", "key": "barcode", "value": str(barcode_variant), "type": "single_line_text_field"})  
            
            # 8. purchase_ok
            purchase_v = getattr(v, 'purchase_ok', None)
            if purchase_v is None:
                purchase_v = getattr(self, 'purchase_ok', False)
            
            v_metafields.append({"namespace": "custom","key": "purchase_ok","value": "true" if purchase_v else "false","type": "single_line_text_field"})
            
            sale_v = getattr(v, 'sale_ok', None)
            if sale_v is None:
                sale_v = getattr(self, 'sale_ok', False)
            v_metafields.append({"namespace": "custom","key": "sale_ok","value": "true" if sale_v else "false","type": "single_line_text_field"})   

            show_v = getattr(v, 'show_availability', None)
            if show_v is None:
                show_v = getattr(self, 'show_availability', False)
            v_metafields.append({"namespace": "custom","key": "show_availability","value": "true" if show_v else "false","type": "single_line_text_field"})   

            # Unit of Measure
            uom_v = getattr(v, 'uom_id', self.uom_id)
            if uom_v:
                v_metafields.append({"namespace": "custom","key": "uom_id","value": str(uom_v.name),"type": "single_line_text_field"})
            
            uom_po_v = getattr(v, 'uom_po_id', self.uom_po_id)
            if uom_po_v:
                v_metafields.append({"namespace": "custom","key": "uom_po_id","value": str(uom_po_v.name),"type": "single_line_text_field"})
            
            website_size_x = getattr(v, 'website_size_x', False) or getattr(self, 'website_size_x', False)
            if website_size_x:
                v_metafields.append({"namespace": "custom","key": "website_size_x","value": str(website_size_x),"type": "single_line_text_field"})
            
            website_size_y = getattr(v, 'website_size_y', False) or getattr(self, 'website_size_y', False)
            if website_size_y:
                v_metafields.append({"namespace": "custom","key": "website_size_y","value": str(website_size_y),"type": "single_line_text_field"})


            if v_metafields:
                variant_dict["metafields"] = v_metafields

            # Map the specific variant values to Shopify option positions (This sets the Variant Name)
            has_option = False
            v_values_log = []
            for i, line in enumerate(attribute_lines[:3]):
                ptav = v.product_template_attribute_value_ids.filtered(lambda x: x.attribute_id == line.attribute_id)
                if ptav:
                    name = ptav[0].name
                    if ptav[0].price_extra > 0:
                        name += f" + {currency_symbol} {ptav[0].price_extra:,.2f}"
                    variant_dict[f"option{i+1}"] = name
                    v_values_log.append(f"Option{i+1}: {name}")
                    has_option = True
                else:
                    variant_dict[f"option{i+1}"] = "Default"
                    v_values_log.append(f"Option{i+1}: Default (Not Found)")

            # Fallback if filtered mapping yielded nothing (but attributes exist)
            if not has_option and v.product_template_attribute_value_ids:
                for i, ptav in enumerate(v.product_template_attribute_value_ids[:3]):
                    name = ptav.name
                    if ptav.price_extra > 0:
                        name += f" + {currency_symbol} {ptav.price_extra:,.2f}"
                    variant_dict[f"option{i+1}"] = name
                    v_values_log.append(f"Fallback Option{i+1}: {name}")
            
            _logger.info("Shopify Export: Prepared Variant SKU %s with values: %s", variant_dict.get('sku'), ", ".join(v_values_log))

            variants_payload.append(variant_dict)

        return variants_payload, options_payload
