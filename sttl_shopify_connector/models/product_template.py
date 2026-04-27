from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import re
import logging
from html import unescape

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    shopify_product_id = fields.Char(string='Shopify Product ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)

    # ─────────────────────────────────────────────────────────────────────────
    # Public actions
    # ─────────────────────────────────────────────────────────────────────────

    def action_export_to_shopify(self):
        success_count = 0
        error_messages = []
        session = requests.Session()

        for product in self:
            try:
                product._export_to_shopify(session=session)
                success_count += 1
            except Exception as e:
                error_messages.append(f"{product.name}: {e}")
                _logger.warning("Shopify Export failed for '%s': %s", product.name, e, exc_info=True)

        error_count = len(error_messages)
        message = _("%s product(s) exported successfully.") % success_count
        if error_count:
            message += _("\n%s product(s) failed:\n%s") % (error_count, "\n".join(error_messages[:5]))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Sync Results'),
                'message': message,
                'type': 'success' if not error_count else 'warning',
                'sticky': bool(error_count),
            },
        }

    @api.model
    def action_scheduled_export_to_shopify(self):
        self = self.with_context(
            auditlog_disabled=True,
            tracking_disable=True,
            no_recompute=True,
        )
        instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
        if not instances:
            _logger.warning("Shopify Scheduled Export: No confirmed instance found.")
            return

        products = self.env['product.template'].search(
            [('is_exported_to_shopify', '=', False), ('product_sku', '!=', False)],
            limit=100,
        )

        # products = self.env['product.template'].search(
        #     [('id', 'in', [
        #         402, 7302, 2400, 971
        #     ])]
        # )

        # for product in products:
        #     product.is_exported_to_shopify = False
        #     product.shopify_product_id = False

        if not products:
            _logger.info("Shopify Scheduled Export: Nothing to export.")
            return

        # Claim row-level locks; skip products already locked by a parallel session
        self.env.cr.execute(
            'SELECT id FROM product_template WHERE id = ANY(%s) FOR UPDATE SKIP LOCKED',
            (list(products.ids),),
        )
        locked_ids = {r[0] for r in self.env.cr.fetchall()}
        products = products.filtered(lambda p: p.id in locked_ids)
        if not products:
            return

        if len(instances) == 1:
            products.filtered(lambda p: not p.shopify_instance_id).write(
                {'shopify_instance_id': instances[-1].id}
            )

        _logger.info("Shopify Scheduled Export: Processing %s product(s).", len(products))
        success = failed = 0
        session = requests.Session()

        for product in products:
            try:
                with self.env.cr.savepoint():
                    product._export_to_shopify(session=session)
                success += 1
            except Exception as e:
                failed += 1
                _logger.warning(
                    "Shopify Scheduled Export: Failed '%s' (ID %s): %s",
                    product.name, product.id, e, exc_info=True,
                )

        _logger.info("Shopify Scheduled Export: Done — %s succeeded, %s failed.", success, failed)

    # ─────────────────────────────────────────────────────────────────────────
    # Metafields
    # ─────────────────────────────────────────────────────────────────────────

    def build_product_metafields(self):
        """Return product-level Shopify metafields (no variant-specific data)."""
        self.ensure_one()
        mfs = []

        def add(key, value, mtype, namespace="custom"):
            if value is None or value is False:
                return
            val_str = str(value).strip()
            if val_str in ("", "False", "false"):
                return
            if mtype == "single_line_text_field":
                val_str = re.sub(r"\s+", " ", val_str)[:255]
            mfs.append({"namespace": namespace, "key": key, "value": val_str, "type": mtype})

        def clean_html(val):
            return unescape(re.sub(r"<[^>]+>", "", val or "")).strip()

        # SKU — only for single-variant products
        if len(self.product_variant_ids) <= 1 and self.default_code:
            add("default_code", self.default_code, "single_line_text_field")

        # Text fields
        add("barcode", self.barcode, "single_line_text_field")
        add("volume", str(self.volume) if self.volume else None, "single_line_text_field")
        add("hs_code", getattr(self, "hs_code", None), "single_line_text_field")
        add("description_sale", getattr(self, "description_sale", None), "single_line_text_field")
        add("website_url", getattr(self, "website_url", None), "single_line_text_field")
        add("variant_color_images", str(getattr(self, "variant_color_images", "") or ""), "single_line_text_field")
        add("out_of_stock_message", getattr(self, "out_of_stock_message", None), "multi_line_text_field")
        add("website_description", clean_html(getattr(self, "website_description", None)), "multi_line_text_field")

        # Numeric fields
        add("weight", str(float(self.weight)) if self.weight else None, "number_decimal")
        wx = getattr(self, "website_size_x", None)
        wy = getattr(self, "website_size_y", None)
        color = getattr(self, "color", None)
        threshold = getattr(self, "available_threshold", None)
        add("website_size_x", str(int(wx)) if wx else None, "number_integer")
        add("website_size_y", str(int(wy)) if wy else None, "number_integer")
        add("color", str(int(color)) if color is not None else None, "number_integer")
        add("available_threshold", str(float(threshold)) if threshold is not None else None, "number_decimal")

        # Boolean fields
        for key in ("purchase_ok", "sale_ok", "show_availability",
                    "has_configurable_attributes", "allow_negative_stock", "have_color_attribute"):
            val = getattr(self, key, None)
            if val is not None:
                add(key, "true" if val else "false", "boolean")

        # Unit of measure
        if self.uom_id:
            add("uom", self.uom_id.name, "single_line_text_field")
            add("uom_id", self.uom_id.name, "single_line_text_field")
        if self.uom_po_id:
            add("uom_po_id", self.uom_po_id.name, "single_line_text_field")

        return mfs

    # ─────────────────────────────────────────────────────────────────────────
    # Core export
    # ─────────────────────────────────────────────────────────────────────────

    def _export_to_shopify(self, session=None):
        self.ensure_one()
        if session is None:
            session = requests.Session()

        # ── Resolve instance ──────────────────────────────────────────────────
        if not self.shopify_instance_id:
            instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
            if len(instances) == 1:
                self.shopify_instance_id = instances[0].id
            else:
                raise UserError(_("Please select a Shopify Instance for: %s") % self.name)

        instance = self.shopify_instance_id
        shop_url = (instance.shop_url or "").replace("https://", "").replace("http://", "").strip("/")
        session.headers.update({
            "X-Shopify-Access-Token": instance.access_token,
            "Content-Type": "application/json",
        })

        # ── Vendor ────────────────────────────────────────────────────────────
        if getattr(self, "product_brand_id", None) and self.product_brand_id:
            vendor = self.product_brand_id.name
        elif self.seller_ids:
            vendor = self.seller_ids[0].partner_id.name
        else:
            vendor = self.name

        # ── Tags ─────────────────────────────────────────────────────────────
        raw_tags = [cat.display_name for cat in getattr(self, "public_categ_ids", []) if cat.display_name]
        raw_tags += getattr(self, "product_tag_ids", self.env["product.tag"]).mapped("name")
        flat_tags = set()
        for t in raw_tags:
            flat_tags.update(p.strip() for p in t.split(" / ") if p.strip())
        tags_str = ", ".join(sorted(flat_tags))

        # ── Body HTML ─────────────────────────────────────────────────────────
        # Short description — used as body_html fallback if no product_tab_description
        ecom_src = (getattr(self, "description_ecommerce", "") or "").strip()
        body_html = ecom_src

        # Images are uploaded once on initial create only.
        # Including images in a PUT tells Shopify to DELETE all existing images and
        # recreate them — resetting image-variant links and making the product appear
        # replaced on every export. Skip image extraction entirely on updates.
        is_initial_create = not bool(self.shopify_product_id)

        # Long description — extract embedded images on initial create only
        product_desc = getattr(self, "product_tab_description", "") or ""
        description_images = []
        b64_inline_count = 0

        if product_desc and is_initial_create:
            # Odoo /web/image/ references: fetch attachment and upload to Shopify image gallery
            for i, path in enumerate(
                    re.findall(r'src=["\'](\/web\/image\/[^?"\']+)["\']', product_desc)
            ):
                try:
                    m = re.search(r'/(\d+)-', path)
                    if m:
                        att = self.env['ir.attachment'].sudo().browse(int(m.group(1)))
                        if att.exists() and att.datas:
                            b64 = att.datas.decode('utf-8') if isinstance(att.datas, bytes) else str(att.datas)
                            description_images.append({
                                "attachment": b64,
                                "filename": f"desc_img_{self.id}_{i}.jpg",
                            })
                except Exception:
                    pass

            # Inline base64 images: replace with placeholder, upload to Shopify image gallery
            for i, (full_src, fmt, b64_data) in enumerate(
                    re.findall(r'src=["\'](data:image/([^;]+);base64,([^"\']+))["\']', product_desc)
            ):
                alt_tag = f"desc_b64_{self.id}_{i}"
                description_images.append({
                    "attachment": b64_data,
                    "filename": f"{alt_tag}.{fmt}",
                    "alt": alt_tag,
                })
                product_desc = product_desc.replace(full_src, f"#DESC_B64_{i}#")
                b64_inline_count += 1

            product_desc = re.sub(r'\s+', ' ', product_desc)

        product_desc = re.sub(r'<p>\s*</p>', '', product_desc, flags=re.IGNORECASE)
        product_desc = re.sub(r'<div>\s*</div>', '', product_desc, flags=re.IGNORECASE)

        # ── Metafields ────────────────────────────────────────────────────────
        product_metafields = self.build_product_metafields()

        seo_title = (getattr(self, "website_meta_title", None) or "")
        seo_description = (getattr(self, "website_meta_description", None) or "")

        metafields = [
            {"namespace": "custom", "key": "id", "value": str(self.id), "type": "single_line_text_field"},
        ]
        if seo_title:
            metafields.append(
                {"namespace": "global", "key": "title_tag", "value": seo_title, "type": "single_line_text_field"})
        if seo_description:
            metafields.append({"namespace": "global", "key": "description_tag", "value": seo_description,
                               "type": "multi_line_text_field"})
        if getattr(self, "website_meta_keywords", None):
            metafields.append(
                {"namespace": "custom", "key": "website_meta_keyword", "value": str(self.website_meta_keywords),
                 "type": "single_line_text_field"})
        if ecom_src:
            clean_ecom = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", ecom_src)).strip()
            if clean_ecom:
                metafields.append({"namespace": "custom", "key": "ecommerce_description", "value": clean_ecom,
                                   "type": "multi_line_text_field"})
        metafields += product_metafields

        # ── Variants + Options ────────────────────────────────────────────────
        variants_payload, options_payload = self._shopify_build_variants_payload(product_metafields)

        if not variants_payload:
            # Simple product: no attribute variants, single Shopify variant
            sku = getattr(self, "product_sku", None) or self.default_code or ""
            bin_loc = getattr(self, "bin_location_id", False)
            variants_payload = [{
                "sku": sku,
                "price": str(self.list_price),
                "weight": float(self.weight) if self.weight else 0.0,
                "barcode": self.barcode or "",
                "taxable": bool(self.taxes_id),
                "metafields": self._build_variant_metafields(self.id, self.default_code, bin_loc, product_metafields),
            }]

        # ── Images (initial create only) ─────────────────────────────────────
        def to_b64(field):
            if not field:
                return None
            return field.decode("utf-8") if isinstance(field, bytes) else str(field)

        images = []
        if is_initial_create:
            if self.image_1920:
                images.append({"attachment": to_b64(self.image_1920), "filename": f"{self.id}_main.jpg"})
            for extra in getattr(self, "product_template_image_ids", []):
                if extra.image_1920:
                    images.append(
                        {"attachment": to_b64(extra.image_1920), "filename": f"{self.id}_extra_{extra.id}.jpg"})
            for v in self.product_variant_ids:
                if v.image_1920 and v.image_1920 != self.image_1920:
                    images.append({
                        "attachment": to_b64(v.image_1920),
                        "filename": f"variant_{v.id}.jpg",
                        "alt": f"variant_{v.id}",
                    })
            images.extend(description_images)

        # ── Assemble payload ──────────────────────────────────────────────────
        product_data = {
            "product": {
                "title": self.name,
                "body_html": product_desc or body_html,
                "vendor": vendor,
                "tags": tags_str,
                "status": "active" if self.sale_ok else "draft",
                "metafields": metafields,
                "variants": variants_payload,
            }
        }
        if options_payload:
            product_data["product"]["options"] = options_payload
        if images:
            product_data["product"]["images"] = images

        # PUT payload: strip metafields and images
        # - Shopify rejects resending existing metafield keys
        # - images are excluded so Shopify does not delete/recreate them on every update
        product_data_put = json.loads(json.dumps(product_data))
        product_data_put["product"].pop("metafields", None)
        product_data_put["product"].pop("images", None)
        for v in product_data_put["product"].get("variants", []):
            v.pop("metafields", None)

        # ── Send to Shopify ───────────────────────────────────────────────────
        response = self._send_to_shopify(session, shop_url, product_data, product_data_put)

        if response.status_code not in (200, 201):
            raise UserError(
                _("Shopify export failed for '%s'. Status %s:\n%s") % (
                    self.name, response.status_code, response.text[:500]
                )
            )

        # ── Process response ──────────────────────────────────────────────────
        shopify_product = response.json().get("product", {})
        self.shopify_product_id = shopify_product.get("id")
        self.is_exported_to_shopify = True

        # SEO via GraphQL — only needed on update (200); POST already includes metafields
        if response.status_code == 200 and (seo_title or seo_description):
            self._apply_seo_graphql(session, shop_url, seo_title, seo_description)

        # Save Shopify variant IDs and sync stock levels
        shopify_images = shopify_product.get("images", [])
        location_id = instance.location_id
        for odoo_v, shopify_v in zip(self.product_variant_ids, shopify_product.get("variants", [])):
            odoo_v.shopify_variant_id = shopify_v.get("id")
            if location_id and shopify_v.get("inventory_item_id"):
                try:
                    session.post(
                        f"https://{shop_url}/admin/api/2024-01/inventory_levels/set.json",
                        data=json.dumps({
                            "location_id": int(location_id),
                            "inventory_item_id": int(shopify_v["inventory_item_id"]),
                            "available": int(odoo_v.qty_available),
                        }),
                        timeout=15,
                    )
                except Exception:
                    pass

        # Link variant-specific images by alt tag
        variant_img_updates = []
        for odoo_v in self.product_variant_ids:
            alt = f"variant_{odoo_v.id}"
            match = next((img for img in shopify_images if img.get("alt") == alt), None)
            if match and odoo_v.shopify_variant_id:
                variant_img_updates.append({"id": odoo_v.shopify_variant_id, "image_id": match["id"]})

        # Replace inline base64 placeholders with Shopify CDN URLs (matched by alt tag)
        original_body = product_desc or body_html
        updated_body = original_body
        if b64_inline_count:
            b64_shopify_imgs = sorted(
                [img for img in shopify_images if img.get("alt", "").startswith(f"desc_b64_{self.id}_")],
                key=lambda img: int(img["alt"].rsplit("_", 1)[-1]),
            )
            for img in b64_shopify_imgs:
                idx = int(img["alt"].rsplit("_", 1)[-1])
                updated_body = updated_body.replace(f"#DESC_B64_{idx}#", img["src"])

        # Final update: apply variant image links and/or updated body_html.
        # Wrapped in try/except so a timeout here does NOT roll back the savepoint —
        # shopify_product_id and is_exported_to_shopify must survive even if this fails.
        if variant_img_updates or updated_body != original_body:
            update_payload = {"product": {"id": self.shopify_product_id}}
            if variant_img_updates:
                update_payload["product"]["variants"] = variant_img_updates
            if updated_body != original_body:
                update_payload["product"]["body_html"] = updated_body
            try:
                session.put(
                    f"https://{shop_url}/admin/api/2024-01/products/{self.shopify_product_id}.json",
                    data=json.dumps(update_payload),
                    timeout=15,
                )
            except Exception as e:
                _logger.warning(
                    "Shopify: image/variant link update failed for '%s' (non-critical): %s",
                    self.name, e,
                )

    # ─────────────────────────────────────────────────────────────────────────
    # HTTP helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _send_to_shopify(self, session, shop_url, product_data, product_data_put):
        """PUT if product exists, POST if new. Handles 404 recovery and 422 retry."""
        if self.shopify_product_id:
            pid = str(self.shopify_product_id).split("/")[-1]
            url = f"https://{shop_url}/admin/api/2024-01/products/{pid}.json"
            resp = session.put(url, data=json.dumps(product_data_put), timeout=60)
            _logger.info("Shopify PUT '%s' → %s", self.name, resp.status_code)

            if resp.status_code == 404:
                _logger.warning("Shopify: '%s' not found by stored ID — searching by Odoo ID.", self.name)
                self.shopify_product_id = False
                existing_id = self._find_shopify_product_by_odoo_id(shop_url, session)
                if existing_id:
                    self.shopify_product_id = existing_id
                    pid = str(existing_id).split("/")[-1]
                    url = f"https://{shop_url}/admin/api/2024-01/products/{pid}.json"
                    resp = session.put(url, data=json.dumps(product_data_put), timeout=60)
                    _logger.info("Shopify PUT (recovered) '%s' → %s", self.name, resp.status_code)
                else:
                    resp = session.post(
                        f"https://{shop_url}/admin/api/2024-01/products.json",
                        data=json.dumps(product_data), timeout=60,
                    )
                    _logger.info("Shopify POST (after 404) '%s' → %s", self.name, resp.status_code)

            if resp.status_code == 422:
                try:
                    variant_errors = resp.json().get("errors", {}).get("variants", [])
                    err_text = " ".join(variant_errors) if isinstance(variant_errors, list) else str(variant_errors)
                    if "do not exist" in err_text or "do not belong" in err_text:
                        retry = json.loads(json.dumps(product_data_put))
                        for v in retry.get("product", {}).get("variants", []):
                            v.pop("id", None)
                        resp = session.put(url, data=json.dumps(retry), timeout=60)
                        _logger.info("Shopify PUT retry (stripped variant IDs) '%s' → %s", self.name, resp.status_code)
                except Exception:
                    pass
        else:
            resp = session.post(
                f"https://{shop_url}/admin/api/2024-01/products.json",
                data=json.dumps(product_data), timeout=60,
            )
            _logger.info("Shopify POST '%s' → %s", self.name, resp.status_code)

        return resp

    def _apply_seo_graphql(self, session, shop_url, seo_title, seo_description):
        """Apply SEO title/description to an existing Shopify product via GraphQL."""
        payload = {
            "query": """
            mutation UpdateProductSEO($input: ProductUpdateInput!) {
              productUpdate(product: $input) {
                userErrors { field message }
              }
            }
            """,
            "variables": {
                "input": {
                    "id": f"gid://shopify/Product/{self.shopify_product_id}",
                    "seo": {"title": seo_title, "description": seo_description},
                }
            },
        }
        try:
            resp = session.post(
                f"https://{shop_url}/admin/api/2024-01/graphql.json",
                json=payload, timeout=30,
            )
            errors = resp.json().get("data", {}).get("productUpdate", {}).get("userErrors", [])
            if errors:
                _logger.warning("Shopify SEO GraphQL errors for '%s': %s", self.name, errors)
        except Exception as e:
            _logger.warning("Shopify SEO GraphQL failed for '%s': %s", self.name, e)

    # ─────────────────────────────────────────────────────────────────────────
    # Variant builder
    # ─────────────────────────────────────────────────────────────────────────

    def _shopify_build_variants_payload(self, product_metafields=None):
        self.ensure_one()
        if product_metafields is None:
            product_metafields = self.build_product_metafields()

        attribute_lines = self.attribute_line_ids
        currency = self.currency_id.symbol or "$"
        bin_loc = getattr(self, "bin_location_id", False)

        # ── Options ──────────────────────────────────────────────────────────
        options_payload = []
        for line in attribute_lines:
            if not line.attribute_id.name:
                continue
            values = []
            for ptav in line.product_template_value_ids:
                label = ptav.name
                if ptav.price_extra > 0:
                    label += f" + {currency} {ptav.price_extra:,.2f}"
                values.append(label)
            options_payload.append({"name": line.attribute_id.name, "values": values or ["Default"]})

        odoo_variants = self.product_variant_ids

        # ── Virtual variant mode ("Never Create Variants") ────────────────────
        if len(odoo_variants) <= 1 and attribute_lines:
            import itertools
            ptav_per_line = [line.product_template_value_ids for line in attribute_lines[:3]]
            if not all(ptav_per_line):
                return [], []

            variants_payload = []
            for combo in itertools.product(*ptav_per_line):
                extra_price = sum(v.price_extra for v in combo)
                sku_base = getattr(self, "product_sku", None) or self.default_code or f"PROD-{self.id}"
                variant_sku = sku_base + "-" + "-".join(v.name[:3].upper() for v in combo)

                vdict = {
                    "sku": variant_sku,
                    "price": str(self.list_price + extra_price),
                    "weight": float(self.weight) if self.weight else 0.0,
                    "barcode": self.barcode or "",
                    "inventory_policy": "continue" if (
                            getattr(self, "out_of_stock_action", None) == "available"
                            or getattr(self, "allow_out_of_stock_order", False)
                    ) else "deny",
                    "metafields": self._build_variant_metafields(
                        self.id, self.default_code, bin_loc, product_metafields
                    ),
                }
                for i, ptav in enumerate(combo):
                    label = ptav.name
                    if ptav.price_extra > 0:
                        label += f" + {currency} {ptav.price_extra:,.2f}"
                    vdict[f"option{i + 1}"] = label

                variants_payload.append(vdict)

            return variants_payload, options_payload

        # ── Standard variant mode ─────────────────────────────────────────────
        variants_payload = []
        for v in odoo_variants:
            sku = getattr(v, "product_sku", None) or getattr(self, "product_sku", None) or v.default_code or ""
            vdict = {
                "sku": sku,
                "price": str(v.lst_price if hasattr(v, "lst_price") else self.list_price),
                "weight": float(v.weight) if getattr(v, "weight", None) else float(self.weight) if self.weight else 0.0,
                "barcode": v.barcode or self.barcode or "",
                "inventory_policy": "continue" if (
                        getattr(self, "out_of_stock_action", None) == "available"
                        or getattr(self, "allow_out_of_stock_order", False)
                ) else "deny",
                "metafields": self._build_variant_metafields(v.id, v.default_code, bin_loc, product_metafields),
            }

            if getattr(v, "shopify_variant_id", None):
                vdict["id"] = int(str(v.shopify_variant_id).split("/")[-1])

            # Map attribute values to option1/option2/option3 positionally
            # Fix: capture `line.attribute_id` at definition time to avoid closure bug
            has_option = False
            for i, line in enumerate(attribute_lines[:3]):
                ptav = v.product_template_attribute_value_ids.filtered(
                    lambda x, attr=line.attribute_id: x.attribute_id == attr
                )
                if ptav:
                    label = ptav[0].name
                    if ptav[0].price_extra > 0:
                        label += f" + {currency} {ptav[0].price_extra:,.2f}"
                    vdict[f"option{i + 1}"] = label
                    has_option = True
                else:
                    vdict[f"option{i + 1}"] = "Default"

            if not has_option:
                for i, ptav in enumerate(v.product_template_attribute_value_ids[:3]):
                    label = ptav.name
                    if ptav.price_extra > 0:
                        label += f" + {currency} {ptav.price_extra:,.2f}"
                    vdict[f"option{i + 1}"] = label

            variants_payload.append(vdict)

        return variants_payload, options_payload

    # ─────────────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────────────

    def _build_variant_metafields(self, variant_id, sku_code, bin_loc, product_metafields):
        """Build variant-level metafields, filtering empty/false values, deduped."""
        bin_loc_name = bin_loc.name if bin_loc else ""
        raw = [
                  {"namespace": "custom", "key": "variant_id", "value": str(variant_id),
                   "type": "single_line_text_field"},
                  {"namespace": "custom", "key": "bin_location_id", "value": bin_loc_name,
                   "type": "single_line_text_field"},
                  {"namespace": "custom", "key": "variant_color_images",
                   "value": str(getattr(self, "variant_color_images", "") or ""), "type": "single_line_text_field"},
                  {"namespace": "custom", "key": "volume", "value": str(self.volume) if self.volume else "0",
                   "type": "single_line_text_field"},
                  {"namespace": "custom", "key": "odoo_sku", "value": sku_code or "", "type": "single_line_text_field"},
              ] + (product_metafields or [])
        return self._dedup_metafields([
            mf for mf in raw
            if mf.get("value") is not None and str(mf["value"]).strip() not in ("", "False", "false")
        ])

    def _find_shopify_product_by_odoo_id(self, shop_url, session):
        """Find a Shopify product by its Odoo ID using a single GraphQL query."""
        payload = {
            "query": """
            query FindProductByOdooId($q: String!) {
              products(first: 1, query: $q) {
                edges { node { legacyResourceId } }
              }
            }
            """,
            "variables": {"q": f"metafield:custom.id:{self.id}"},
        }
        try:
            resp = session.post(
                f"https://{shop_url}/admin/api/2024-01/graphql.json",
                json=payload, timeout=15,
            )
            if resp.status_code == 200:
                edges = resp.json().get("data", {}).get("products", {}).get("edges", [])
                if edges:
                    return edges[0]["node"]["legacyResourceId"]
        except Exception as e:
            _logger.warning("Shopify GraphQL lookup failed for Odoo ID %s: %s", self.id, e)
        return False

    @staticmethod
    def _dedup_metafields(metafields):
        seen = set()
        result = []
        for mf in metafields:
            k = (mf.get("namespace"), mf.get("key"))
            if k not in seen:
                seen.add(k)
                result.append(mf)
        return result
