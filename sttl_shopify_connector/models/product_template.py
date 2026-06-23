from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import re
import itertools
import logging
import csv
import os
from html import unescape
from datetime import datetime, timezone
from odoo.tools import config

_logger = logging.getLogger(__name__)
API = "2024-01"


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    shopify_product_id = fields.Char(string='Shopify Product ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)

    # ─────────────────────────────────────────────────────────────────────────
    # Public actions
    # ─────────────────────────────────────────────────────────────────────────

    def action_export_to_shopify(self):
        """Manual export — called from button on product form/list."""
        errors = []
        by_instance = {}
        for p in self:
            inst = p._resolve_instance()
            by_instance.setdefault(inst, []).append(p)

        for instance, products in by_instance.items():
            session = self._make_session(instance)
            for product in products:
                try:
                    product._export_to_shopify(session, instance)
                    product._write_export_log('success', instance)
                except Exception as e:
                    errors.append(f"{product.name}: {e}")
                    product._write_export_log('error', instance, str(e))
                    _logger.warning("Shopify export failed for '%s': %s", product.name, e, exc_info=True)

        message = _("%s product(s) exported successfully.") % (len(self) - len(errors))
        if errors:
            message += _("\n%s failed:\n%s") % (len(errors), "\n".join(errors[:5]))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Sync'),
                'message': message,
                'type': 'warning' if errors else 'success',
                'sticky': bool(errors),
            },
        }

    @api.model
    def action_scheduled_export_to_shopify(self):
        """Scheduled action — exports unsynced products, safe for parallel runs."""
        self = self.with_context(auditlog_disabled=True, tracking_disable=True, no_recompute=True)

        instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
        if not instances:
            _logger.warning("Shopify scheduled export: no confirmed instance.")
            return

        products = self.env['product.template'].search(
            [('is_exported_to_shopify', '=', False), ('product_sku', '!=', False)],
            limit=120,
        )

        if not products:
            return

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
                {'shopify_instance_id': instances[0].id}
            )

        by_instance = {}
        for p in products:
            if p.shopify_instance_id:
                by_instance.setdefault(p.shopify_instance_id, []).append(p)

        success = failed = 0
        for instance, group in by_instance.items():
            session = self._make_session(instance)
            for product in group:
                try:
                    with self.env.cr.savepoint():
                        product._export_to_shopify(session, instance)
                    product._write_export_log('success', instance)
                    success += 1
                except Exception as e:
                    product._write_export_log('error', instance, str(e))
                    failed += 1
                    _logger.warning(
                        "Shopify scheduled export: failed '%s' (ID %s): %s",
                        product.name, product.id, e, exc_info=True,
                    )

        _logger.info("Shopify scheduled export: %s succeeded, %s failed.", success, failed)

    # ─────────────────────────────────────────────────────────────────────────
    # Core export
    # ─────────────────────────────────────────────────────────────────────────

    def _export_to_shopify(self, session, instance):
        """
        Export this product to Shopify.
        - PUT  when shopify_product_id is set (update existing).
        - POST only when no existing product can be found (new product).
        - Never creates duplicates.
        """
        self.ensure_one()
        shop_url = (instance.shop_url or "").replace("https://", "").replace("http://", "").strip("/")
        is_new = not bool(self.shopify_product_id)

        product_metafields = self._build_product_metafields()
        variants, options = self._build_variants(product_metafields)
        if not variants:
            variants = [self._single_variant_payload()]

        body_html, desc_images, b64_count = self._build_body_html()
        images = self._collect_images(desc_images)

        payload = {
            "product": {
                "title": self.name,
                "body_html": body_html,
                "vendor": self._vendor(),
                "tags": self._tags(),
                "status": "active" if self.sale_ok else "draft",
                "published_at": datetime.now(timezone.utc).isoformat() if getattr(self, 'is_published', False) else None,
                "variants": variants,
                "metafields": self._top_level_metafields(product_metafields),
            }
        }
        if options:
            payload["product"]["options"] = options
        if images:
            payload["product"]["images"] = images

        resp = self._send(session, shop_url, payload)

        if resp.status_code not in (200, 201):
            raise UserError(
                _("Shopify export failed for '%s'. Status %s:\n%s")
                % (self.name, resp.status_code, resp.text[:500])
            )

        shopify_product = resp.json()["product"]
        self._write_shopify_sync({
            'shopify_product_id': str(shopify_product["id"]),
            'is_exported_to_shopify': True,
        })

        seo_title = getattr(self, "website_meta_title", "") or ""
        seo_desc = getattr(self, "website_meta_description", "") or ""
        if resp.status_code == 200:
            update_metafields = self._build_product_metafields(include_empty=True)
            self._push_metafields(session, shop_url, shopify_product["id"], self._top_level_metafields(update_metafields, include_empty=True))
            if seo_title or seo_desc:
                self._push_seo(session, shop_url, seo_title, seo_desc)

        self._sync_variants(session, shop_url, shopify_product)
        self._finalize(session, shop_url, shopify_product.get("images", []), body_html, b64_count)

    # ─────────────────────────────────────────────────────────────────────────
    # HTTP — POST vs PUT with 404/422 recovery
    # ─────────────────────────────────────────────────────────────────────────

    def _send(self, session, shop_url, payload):
        """
        PUT  → product has a stored Shopify ID (update, never creates duplicate).
        POST → no stored ID or confirmed missing on Shopify (new product only).

        PUT payload strips metafields + images so Shopify doesn't reset them on update.
        """
        base = f"https://{shop_url}/admin/api/{API}/products"

        if not self.shopify_product_id:
            resp = session.post(f"{base}.json", data=json.dumps(payload), timeout=60)
            _logger.info("Shopify POST '%s' → %s", self.name, resp.status_code)
            return resp

        put_payload = json.loads(json.dumps(payload))
        put_payload["product"].pop("metafields", None)
        put_payload["product"].pop("images", None)
        for v in put_payload["product"].get("variants", []):
            v.pop("metafields", None)
            v.pop("inventory_quantity", None)

        pid = str(self.shopify_product_id).split("/")[-1]
        url = f"{base}/{pid}.json"
        resp = session.put(url, data=json.dumps(put_payload), timeout=60)
        _logger.info("Shopify PUT '%s' → %s", self.name, resp.status_code)

        # 404: stored ID is stale — search by Odoo metafield before creating new
        if resp.status_code == 404:
            _logger.warning("Shopify: '%s' not found by stored ID — searching by Odoo ID.", self.name)
            self._write_shopify_sync({'shopify_product_id': False})
            found_id = self._find_by_odoo_id(shop_url, session)
            if found_id:
                self._write_shopify_sync({'shopify_product_id': str(found_id)})
                url = f"{base}/{found_id}.json"
                resp = session.put(url, data=json.dumps(put_payload), timeout=60)
            else:
                resp = session.post(f"{base}.json", data=json.dumps(payload), timeout=60)
            _logger.info("Shopify recovery '%s' → %s", self.name, resp.status_code)

        # 422: stale variant IDs — strip and retry PUT
        if resp.status_code == 422:
            try:
                errs = resp.json().get("errors", {}).get("variants", [])
                err_text = " ".join(errs) if isinstance(errs, list) else str(errs)
                if "do not exist" in err_text or "do not belong" in err_text:
                    retry = json.loads(json.dumps(put_payload))
                    for v in retry["product"].get("variants", []):
                        v.pop("id", None)
                    resp = session.put(url, data=json.dumps(retry), timeout=60)
                    _logger.info("Shopify PUT retry (stripped variant IDs) '%s' → %s", self.name, resp.status_code)
            except Exception:
                pass

        return resp

    # ─────────────────────────────────────────────────────────────────────────
    # Variant + option builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_variants(self, product_metafields):
        """Return (variants_payload, options_payload). Both empty = simple product."""
        self.ensure_one()
        lines = self.attribute_line_ids
        if not lines:
            return [], []

        currency = self.currency_id.symbol or "$"

        def label(ptav):
            return ptav.name + (f" + {currency} {ptav.price_extra:,.2f}" if ptav.price_extra > 0 else "")

        options = [
            {"name": line.attribute_id.name,
             "values": [label(p) for p in line.product_template_value_ids] or ["Default"]}
            for line in lines if line.attribute_id.name
        ]

        odoo_variants = self.product_variant_ids

        # Virtual mode: Odoo never created actual variant records
        if len(odoo_variants) <= 1:
            ptav_per_line = [line.product_template_value_ids for line in lines[:3]]
            if not all(ptav_per_line):
                return [], []
            sku_base = getattr(self, "product_sku", None) or self.default_code or f"PROD-{self.id}"
            variants = []
            for combo in itertools.product(*ptav_per_line):
                extra = sum(v.price_extra for v in combo)
                vdict = {
                    "sku": sku_base + "-" + "-".join(v.name[:3].upper() for v in combo),
                    "price": str(self.list_price + extra),
                    "weight": float(self.weight) if self.weight else 0.0,
                    "barcode": self.barcode or "",
                    "inventory_management": None,
                    "metafields": self._variant_metafields(self.id, self.default_code),
                }
                for i, ptav in enumerate(combo):
                    vdict[f"option{i + 1}"] = label(ptav)
                variants.append(vdict)
            return variants, options

        # Standard mode: one Shopify variant per Odoo variant
        variants = []
        for v in odoo_variants:
            sku = getattr(v, "product_sku", None) or getattr(self, "product_sku", None) or v.default_code or ""
            vdict = {
                "sku": sku,
                "price": str(v.lst_price if hasattr(v, "lst_price") else self.list_price),
                "weight": float(v.weight) if getattr(v, "weight", None) else float(self.weight) if self.weight else 0.0,
                "barcode": v.barcode or self.barcode or "",
                "inventory_management": None,
                "metafields": self._variant_metafields(v.id, v.default_code),
            }
            if getattr(v, "shopify_variant_id", None):
                vdict["id"] = int(str(v.shopify_variant_id).split("/")[-1])

            for i, line in enumerate(lines[:3]):
                ptav = v.product_template_attribute_value_ids.filtered(
                    lambda x, attr=line.attribute_id: x.attribute_id == attr
                )
                vdict[f"option{i + 1}"] = label(ptav[0]) if ptav else "Default"

            variants.append(vdict)
        return variants, options

    def _single_variant_payload(self):
        return {
            "sku": getattr(self, "product_sku", None) or self.default_code or "",
            "price": str(self.list_price),
            "weight": float(self.weight) if self.weight else 0.0,
            "barcode": self.barcode or "",
            "taxable": bool(self.taxes_id),
            "inventory_management": None,
            "metafields": self._variant_metafields(self.id, self.default_code),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Metafields
    # ─────────────────────────────────────────────────────────────────────────

    def _build_product_metafields(self, include_empty=False):
        self.ensure_one()
        mfs = []
        _TEXT_TYPES = ("single_line_text_field", "multi_line_text_field")

        def add(key, value, mtype, namespace="custom"):
            is_empty = value is None or value is False or (mtype != "boolean" and str(value).strip() in ("", "False", "false"))
            if is_empty:
                if not include_empty or mtype not in _TEXT_TYPES:
                    return
                val = ""
            else:
                val = str(value).strip()
                if mtype in _TEXT_TYPES:
                    val = unescape(re.sub(r"<[^>]+>", "", val)).strip()
            if mtype == "single_line_text_field":
                val = re.sub(r"\s+", " ", val)[:255]
            mfs.append({"namespace": namespace, "key": key, "value": val, "type": mtype})

        clean = lambda v: unescape(re.sub(r"<[^>]+>", "", v or "")).strip()

        if len(self.product_variant_ids) <= 1 and self.default_code:
            add("default_code", self.default_code, "single_line_text_field")

        add("barcode", self.barcode, "single_line_text_field")
        add("volume", str(self.volume) if self.volume else None, "single_line_text_field")
        add("weight", str(float(self.weight)) if self.weight else None, "number_decimal")
        add("hs_code", getattr(self, "hs_code", None), "single_line_text_field")
        add("description_sale", getattr(self, "description_sale", None), "single_line_text_field")
        add("website_url", getattr(self, "website_url", None), "single_line_text_field")
        add("variant_color_images", str(getattr(self, "variant_color_images", "") or ""), "single_line_text_field")
        add("out_of_stock_message", getattr(self, "out_of_stock_message", None), "multi_line_text_field")
        add("website_description", clean(getattr(self, "website_description", None)), "multi_line_text_field")

        for key in ("website_size_x", "website_size_y", "color"):
            val = getattr(self, key, None)
            if val is not None:
                add(key, str(int(val)), "number_integer")

        val = getattr(self, "available_threshold", None)
        if val is not None:
            add("available_threshold", str(float(val)), "number_decimal")

        for key in ("purchase_ok", "sale_ok", "show_availability",
                    "has_configurable_attributes", "allow_negative_stock", "have_color_attribute", "is_combo"):
            val = getattr(self, key, None)
            if val is not None:
                add(key, "true" if val else "false", "boolean")

        if self.uom_id:
            add("uom", self.uom_id.name, "single_line_text_field")
            add("uom_id", self.uom_id.name, "single_line_text_field")
        if self.uom_po_id:
            add("uom_po_id", self.uom_po_id.name, "single_line_text_field")

        return mfs

    def _top_level_metafields(self, product_metafields, include_empty=False):
        mfs = [{"namespace": "custom", "key": "id", "value": str(self.id), "type": "single_line_text_field"}]

        seo_title = getattr(self, "website_meta_title", "") or ""
        seo_desc = getattr(self, "website_meta_description", "") or ""
        ecom = (getattr(self, "description_ecommerce", "") or "").strip()
        keywords = str(getattr(self, "website_meta_keywords", "") or "")

        if seo_title or include_empty:
            mfs.append({"namespace": "global", "key": "title_tag", "value": seo_title, "type": "single_line_text_field"})
        if seo_desc or include_empty:
            mfs.append({"namespace": "global", "key": "description_tag", "value": seo_desc, "type": "multi_line_text_field"})
        if keywords or include_empty:
            mfs.append({"namespace": "custom", "key": "website_meta_keyword", "value": keywords, "type": "single_line_text_field"})
        if ecom or include_empty:
            clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", ecom)).strip() if ecom else ""
            mfs.append({"namespace": "custom", "key": "ecommerce_description", "value": clean, "type": "multi_line_text_field"})

        return mfs + product_metafields

    def _variant_metafields(self, variant_id, sku_code):
        """Variant-only metafields — does not repeat product-level fields."""
        bin_loc = getattr(self, "bin_location_id", False)
        raw = [
            {"namespace": "custom", "key": "variant_id", "value": str(variant_id), "type": "single_line_text_field"},
            {"namespace": "custom", "key": "bin_location_id", "value": bin_loc.name if bin_loc else "",
             "type": "single_line_text_field"},
            {"namespace": "custom", "key": "variant_color_images",
             "value": str(getattr(self, "variant_color_images", "") or ""), "type": "single_line_text_field"},
            {"namespace": "custom", "key": "volume", "value": str(self.volume) if self.volume else "0",
             "type": "single_line_text_field"},
            {"namespace": "custom", "key": "odoo_sku", "value": sku_code or "", "type": "single_line_text_field"},
        ]
        return self._dedup_metafields(raw)

    # ─────────────────────────────────────────────────────────────────────────
    # Body HTML + images
    # ─────────────────────────────────────────────────────────────────────────

    def _build_body_html(self):
        """Return (body_html, description_images, b64_inline_count)."""
        ecom = (getattr(self, "description_ecommerce", "") or "").strip()
        desc = getattr(self, "product_tab_description", "") or ""
        desc_images, b64_count = [], 0

        if desc:
            for i, path in enumerate(re.findall(r'src=["\'](\/web\/image\/[^?"\']+)["\']', desc)):
                m = re.search(r'/(\d+)-', path)
                if m:
                    att = self.env['ir.attachment'].sudo().browse(int(m.group(1)))
                    if att.exists() and att.datas:
                        b64 = att.datas.decode('utf-8') if isinstance(att.datas, bytes) else str(att.datas)
                        desc_images.append({"attachment": b64, "filename": f"desc_img_{self.id}_{i}.jpg"})

            for i, (full_src, fmt, b64_data) in enumerate(
                    re.findall(r'src=["\'](data:image/([^;]+);base64,([^"\']+))["\']', desc)
            ):
                alt = f"desc_b64_{self.id}_{i}"
                desc_images.append({"attachment": b64_data, "filename": f"{alt}.{fmt}", "alt": alt})
                desc = desc.replace(full_src, f"#DESC_B64_{i}#")
                b64_count += 1

            desc = re.sub(r'\s+', ' ', desc)

        desc = re.sub(r'<p>\s*</p>|<div>\s*</div>', '', desc, flags=re.IGNORECASE)
        return desc or ecom, desc_images, b64_count

    def _collect_images(self, desc_images):
        def b64(f):
            return f.decode('utf-8') if isinstance(f, bytes) else str(f)

        images = []
        if self.image_1920:
            images.append({"attachment": b64(self.image_1920), "filename": f"{self.id}_main.jpg"})
        for extra in getattr(self, "product_template_image_ids", []):
            if extra.image_1920:
                images.append({"attachment": b64(extra.image_1920), "filename": f"{self.id}_extra_{extra.id}.jpg"})
        for v in self.product_variant_ids:
            if v.image_1920 and v.image_1920 != self.image_1920:
                images.append(
                    {"attachment": b64(v.image_1920), "filename": f"variant_{v.id}.jpg", "alt": f"variant_{v.id}"})
        return images + desc_images

    # ─────────────────────────────────────────────────────────────────────────
    # Post-send helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _sync_variants(self, session, shop_url, shopify_product):
        """Match variants by SKU (not position), sync metafields and stock levels."""
        shopify_by_sku = {v["sku"]: v for v in shopify_product.get("variants", []) if v.get("sku")}
        for odoo_v in self.product_variant_ids:
            sku = getattr(odoo_v, "product_sku", None) or odoo_v.default_code or ""
            shopify_v = shopify_by_sku.get(sku)
            if not shopify_v:
                continue
            try:
                odoo_v.write({'shopify_variant_id': str(shopify_v["id"])})
            except RuntimeError:
                self.env.cr.execute(
                    'UPDATE product_product SET shopify_variant_id = %s WHERE id = %s',
                    [str(shopify_v["id"]), odoo_v.id]
                )
                odoo_v.invalidate_recordset(['shopify_variant_id'])

            self._push_metafields(
                session, shop_url, shopify_v["id"],
                self._variant_metafields(odoo_v.id, odoo_v.default_code),
                owner_type="ProductVariant",
            )



    def _finalize(self, session, shop_url, shopify_images, original_body, b64_count):
        """Link variant images and swap base64 placeholders for CDN URLs. Non-critical."""
        variant_updates = []
        for odoo_v in self.product_variant_ids:
            match = next((img for img in shopify_images if img.get("alt") == f"variant_{odoo_v.id}"), None)
            if match and getattr(odoo_v, "shopify_variant_id", None):
                variant_updates.append({"id": odoo_v.shopify_variant_id, "image_id": match["id"]})

        updated_body = original_body
        if b64_count:
            for img in sorted(
                    [i for i in shopify_images if (i.get("alt") or "").startswith(f"desc_b64_{self.id}_")],
                    key=lambda i: int(i["alt"].rsplit("_", 1)[-1]),
            ):
                updated_body = updated_body.replace(
                    f"#DESC_B64_{img['alt'].rsplit('_', 1)[-1]}#", img["src"]
                )

        if not variant_updates and updated_body == original_body:
            return

        patch = {"product": {"id": self.shopify_product_id}}
        if variant_updates:
            patch["product"]["variants"] = variant_updates
        if updated_body != original_body:
            patch["product"]["body_html"] = updated_body
        try:
            session.put(
                f"https://{shop_url}/admin/api/{API}/products/{self.shopify_product_id}.json",
                data=json.dumps(patch), timeout=15,
            )
        except Exception as e:
            _logger.warning("Shopify: finalize failed for '%s' (non-critical): %s", self.name, e)

    def _push_seo(self, session, shop_url, seo_title, seo_desc):
        try:
            resp = session.post(
                f"https://{shop_url}/admin/api/{API}/graphql.json",
                json={
                    "query": "mutation UpdateProductSEO($input: ProductUpdateInput!) { productUpdate(product: $input) { userErrors { field message } } }",
                    "variables": {"input": {
                        "id": f"gid://shopify/Product/{self.shopify_product_id}",
                        "seo": {"title": seo_title, "description": seo_desc},
                    }},
                },
                timeout=30,
            )
            errors = resp.json().get("data", {}).get("productUpdate", {}).get("userErrors", [])
            if errors:
                _logger.warning("Shopify SEO errors for '%s': %s", self.name, errors)
        except Exception as e:
            _logger.warning("Shopify SEO failed for '%s': %s", self.name, e)

    def _push_metafields(self, session, shop_url, resource_id, metafields, owner_type="Product"):
        """Set non-empty metafields via GraphQL metafieldsSet; delete empty ones via REST.
        Shopify rejects empty string values on metafieldsSet, so clearing requires deletion."""
        if not metafields:
            return

        rid = str(resource_id).split('/')[-1]
        to_set = [mf for mf in metafields if str(mf.get("value", "")).strip()]
        to_clear = [mf for mf in metafields if not str(mf.get("value", "")).strip()]

        if to_set:
            owner_gid = f"gid://shopify/{owner_type}/{rid}"
            inputs = [
                {
                    "ownerId": owner_gid,
                    "namespace": mf["namespace"],
                    "key": mf["key"],
                    "value": mf["value"],
                    "type": mf["type"],
                }
                for mf in to_set
            ]
            for i in range(0, len(inputs), 25):
                chunk = inputs[i:i + 25]
                try:
                    resp = session.post(
                        f"https://{shop_url}/admin/api/{API}/graphql.json",
                        json={
                            "query": "mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $metafields) { userErrors { field message code } } }",
                            "variables": {"metafields": chunk},
                        },
                        timeout=30,
                    )
                    errors = resp.json().get("data", {}).get("metafieldsSet", {}).get("userErrors", [])
                    if errors:
                        _logger.warning("Shopify metafields update errors for '%s': %s", self.name, errors)
                except Exception as e:
                    _logger.warning("Shopify metafields update failed for '%s': %s", self.name, e)

        if to_clear:
            if owner_type == "ProductVariant":
                list_url = f"https://{shop_url}/admin/api/{API}/variants/{rid}/metafields.json"
                delete_base = f"https://{shop_url}/admin/api/{API}/variants/{rid}/metafields"
            else:
                list_url = f"https://{shop_url}/admin/api/{API}/products/{rid}/metafields.json"
                delete_base = f"https://{shop_url}/admin/api/{API}/products/{rid}/metafields"
            try:
                resp = session.get(list_url, timeout=15)
                if resp.status_code == 200:
                    existing = {
                        (m["namespace"], m["key"]): m["id"]
                        for m in resp.json().get("metafields", [])
                    }
                    for mf in to_clear:
                        mf_id = existing.get((mf["namespace"], mf["key"]))
                        if mf_id:
                            try:
                                session.delete(f"{delete_base}/{mf_id}.json", timeout=15)
                            except Exception as e:
                                _logger.warning("Shopify metafield delete failed for '%s' [%s.%s]: %s", self.name, mf["namespace"], mf["key"], e)
            except Exception as e:
                _logger.warning("Shopify metafields list failed for '%s': %s", self.name, e)

    def _find_by_odoo_id(self, shop_url, session):
        """GraphQL lookup — prevents duplicate creation on 404."""
        try:
            resp = session.post(
                f"https://{shop_url}/admin/api/{API}/graphql.json",
                json={
                    "query": "query Find($q: String!) { products(first: 1, query: $q) { edges { node { legacyResourceId } } } }",
                    "variables": {"q": f"metafield:custom.id:{self.id}"},
                },
                timeout=15,
            )
            if resp.status_code == 200:
                edges = resp.json().get("data", {}).get("products", {}).get("edges", [])
                if edges:
                    return edges[0]["node"]["legacyResourceId"]
        except Exception as e:
            _logger.warning("Shopify GraphQL lookup failed for Odoo ID %s: %s", self.id, e)
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_instance(self):
        if self.shopify_instance_id:
            return self.shopify_instance_id
        instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
        if len(instances) == 1:
            self.shopify_instance_id = instances[0].id
            return instances[0]
        raise UserError(_("Please select a Shopify Instance for: %s") % self.name)

    def _vendor(self):
        if getattr(self, "product_brand_id", None):
            return self.product_brand_id.name
        return self.seller_ids[0].partner_id.name if self.seller_ids else self.name

    def _tags(self):
        raw = [c.display_name for c in getattr(self, "public_categ_ids", []) if c.display_name]
        raw += getattr(self, "product_tag_ids", self.env["product.tag"]).mapped("name")
        flat = set()
        for t in raw:
            flat.update(p.strip() for p in t.split(" / ") if p.strip())
        return ", ".join(sorted(flat))

    def _write_shopify_sync(self, vals):
        """Write Shopify sync fields safely in both HTTP and cron contexts.
        Falls back to direct SQL when audit trail raises RuntimeError (no HTTP request in cron)."""
        try:
            self.write(vals)
        except RuntimeError:
            for col, val in vals.items():
                self.env.cr.execute(
                    f'UPDATE {self._table} SET "{col}" = %s WHERE id = %s',
                    [val, self.id]
                )
            self.invalidate_recordset(list(vals.keys()))

    @staticmethod
    def _make_session(instance):
        s = requests.Session()
        s.headers.update({"X-Shopify-Access-Token": instance.access_token, "Content-Type": "application/json"})
        return s

    @staticmethod
    def _dedup_metafields(metafields):
        seen, result = set(), []
        for mf in metafields:
            k = (mf.get("namespace"), mf.get("key"))
            if k not in seen:
                seen.add(k)
                result.append(mf)
        return result

    def _write_export_log(self, status, instance, error_message=None):
        try:
            log_dir = os.path.join(config.get('data_dir', '/tmp'), 'shopify_logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'product_export.csv')
            file_exists = os.path.isfile(log_file)
            with open(log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        'Export Date', 'Product Name', 'Odoo ID',
                        'Shopify Product ID', 'Instance', 'Status', 'Error Message',
                    ])
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    self.name,
                    self.id,
                    self.shopify_product_id or '',
                    instance.name if instance else '',
                    status,
                    error_message or '',
                ])
        except Exception as e:
            _logger.warning("Failed to write product export log for '%s': %s", self.name, e)