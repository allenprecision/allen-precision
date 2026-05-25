from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging
import time

_logger = logging.getLogger(__name__)

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

    def action_cleanup_duplicate_shopify_products(self):
        """Delete duplicate Shopify products, keeping the one whose ID is stored in Odoo.

        Strategy:
        - Fetch every product from Shopify (paginated, fields=id,title only).
        - Group by exact title; skip groups with only one product.
        - For each duplicate group, keep the Shopify product whose ID is stored
          in product.template.shopify_product_id. Delete all others.
        - If no product in the group matches an Odoo record, skip it entirely
          (never delete blindly).
        """
        self.ensure_one()
        shop_url = (self.shop_url or "").replace('https://', '').replace('http://', '').strip('/')

        session = requests.Session()
        session.headers.update({
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        })

        # ── 1. Build set of Shopify IDs that Odoo wants to keep ──────────────
        odoo_products = self.env['product.template'].search([
            ('shopify_instance_id', '=', self.id),
            ('shopify_product_id', '!=', False),
            ('shopify_product_id', '!=', ''),
        ])
        # Map shopify_id (str) -> odoo product for quick lookup
        odoo_id_map = {p.shopify_product_id: p for p in odoo_products}

        # ── 2. Fetch all Shopify products (paginated) ─────────────────────────
        all_shopify = {}  # title -> [{'id': ..., 'title': ...}, ...]
        url = f"https://{shop_url}/admin/api/2024-01/products.json"
        params = {"fields": "id,title", "limit": 250}

        while url:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                raise UserError(_("Failed to fetch Shopify products: %s %s") % (resp.status_code, resp.text))
            for p in resp.json().get("products", []):
                all_shopify.setdefault(p["title"], []).append(p)
            # Shopify cursor pagination via Link header
            url = None
            params = {}
            for part in resp.headers.get("Link", "").split(","):
                if 'rel="next"' in part:
                    # extract URL from <...>
                    url = part.strip().split(";")[0].strip().lstrip("<").rstrip(">")
                    break

        # ── 3. Delete duplicates ──────────────────────────────────────────────
        deleted = 0
        failed = 0
        skipped_no_odoo_match = 0

        for title, products in all_shopify.items():
            if len(products) <= 1:
                continue

            # Find which product in this group is linked to Odoo
            keep_id = None
            for p in products:
                if str(p["id"]) in odoo_id_map:
                    keep_id = p["id"]
                    break

            if keep_id is None:
                skipped_no_odoo_match += 1
                _logger.warning("Shopify cleanup: skipping '%s' — no Odoo match among IDs %s",
                                title, [p["id"] for p in products])
                continue

            for p in products:
                if p["id"] == keep_id:
                    continue
                del_url = f"https://{shop_url}/admin/api/2024-01/products/{p['id']}.json"
                del_resp = session.delete(del_url, timeout=30)
                if del_resp.status_code == 200:
                    deleted += 1
                    _logger.info("Shopify cleanup: deleted product id=%s title='%s'", p["id"], title)
                else:
                    failed += 1
                    _logger.warning("Shopify cleanup: failed to delete id=%s (%s): %s",
                                    p["id"], del_resp.status_code, del_resp.text)

        # ── 4. Report ─────────────────────────────────────────────────────────
        parts = [_("%d duplicate product(s) deleted from Shopify.") % deleted]
        if failed:
            parts.append(_("%d deletion(s) failed — check server logs.") % failed)
        if skipped_no_odoo_match:
            parts.append(_("%d title group(s) skipped (no matching Odoo record found).") % skipped_no_odoo_match)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Duplicate Cleanup'),
                'message': " ".join(parts),
                'type': 'warning' if (failed or skipped_no_odoo_match) else 'success',
                'sticky': True,
            },
        }

    def action_clear_shopify_product_type(self):
        """Set product_type to empty string on all Shopify products linked to this instance."""
        self.ensure_one()
        shop_url = (self.shop_url or "").replace('https://', '').replace('http://', '').strip('/')

        session = requests.Session()
        session.headers.update({
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        })

        odoo_products = self.env['product.template'].search([
            ('shopify_instance_id', '=', self.id),
            ('shopify_product_id', '!=', False),
            ('shopify_product_id', '!=', ''),
        ])

        updated = 0
        failed = 0

        for product in odoo_products:
            pid = str(product.shopify_product_id).split('/')[-1]
            url = f"https://{shop_url}/admin/api/2024-01/products/{pid}.json"
            resp = session.put(url, data=json.dumps({"product": {"id": pid, "product_type": ""}}), timeout=30)
            if resp.status_code == 200:
                updated += 1
            else:
                failed += 1
                _logger.warning("Clear product_type failed for '%s' (id=%s): %s %s",
                                product.name, pid, resp.status_code, resp.text)

        parts = [_("%d product(s) updated — product type cleared.") % updated]
        if failed:
            parts.append(_("%d update(s) failed — check server logs.") % failed)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Clear Product Type'),
                'message': " ".join(parts),
                'type': 'warning' if failed else 'success',
                'sticky': True,
            },
        }

    def action_find_duplicate_shopify_customers(self):
        """Delete duplicate Shopify customers where the same Odoo partner
        was exported more than once.

        Strategy:
        - Fetch ALL customers from Shopify (paginated bulk, same as before).
        - Group by full name.
        - For each duplicate name group, keep the one whose ID is in Odoo
          (shopify_customer_id). For remaining candidates, verify by fetching
          metafield custom.id — only delete if it matches the Odoo partner ID.
        """
        self.ensure_one()
        shop_url = (self.shop_url or "").replace('https://', '').replace('http://', '').strip('/')

        session = requests.Session()
        session.headers.update({
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        })

        # ── 1. Build Odoo ID map: shopify_customer_id → partner ──────────────
        odoo_partners = self.env['res.partner'].search([
            ('shopify_instance_id', '=', self.id),
            ('shopify_customer_id', '!=', False),
            ('shopify_customer_id', '!=', ''),
        ])
        odoo_id_map = {p.shopify_customer_id: p for p in odoo_partners}

        # ── 2. Fetch all Shopify customers (paginated bulk) ───────────────────
        name_map = {}
        url = f"https://{shop_url}/admin/api/2024-01/customers.json"
        params = {"fields": "id,first_name,last_name", "limit": 250}

        while url:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                raise UserError(_("Failed to fetch Shopify customers: %s %s") % (resp.status_code, resp.text))
            for c in resp.json().get("customers", []):
                full_name = f"{(c.get('first_name') or '').strip()} {(c.get('last_name') or '').strip()}".strip().lower()
                if full_name:
                    name_map.setdefault(full_name, []).append(c)
            url = None
            params = {}
            for part in resp.headers.get("Link", "").split(","):
                if 'rel="next"' in part:
                    url = part.strip().split(";")[0].strip().lstrip("<").rstrip(">")
                    break

        # ── 3. Process duplicate name groups ─────────────────────────────────
        deleted = failed = skipped_no_match = 0

        for name, customers in name_map.items():
            if len(customers) <= 1:
                continue

            # Find which customer in this group is the correct Odoo-linked one
            keep_id = None
            odoo_partner = None
            for c in customers:
                sid = str(c["id"])
                if sid in odoo_id_map:
                    keep_id = sid
                    odoo_partner = odoo_id_map[sid]
                    break

            if not keep_id or not odoo_partner:
                skipped_no_match += 1
                _logger.warning(
                    "Duplicate cleanup: skipping '%s' — no Odoo match among IDs %s",
                    name, [c["id"] for c in customers],
                )
                continue

            # For each candidate (not the correct one), verify via metafield custom.id
            for c in customers:
                if str(c["id"]) == keep_id:
                    continue

                # Fetch metafield custom.id for this candidate
                mf_resp = session.get(
                    f"https://{shop_url}/admin/api/2024-01/customers/{c['id']}/metafields.json",
                    params={"namespace": "custom", "key": "id"},
                    timeout=15,
                )
                if mf_resp.status_code != 200:
                    _logger.warning("Duplicate cleanup: metafield fetch failed for Shopify ID %s", c['id'])
                    continue

                odoo_id_in_shopify = None
                for mf in mf_resp.json().get('metafields', []):
                    if mf.get('namespace') == 'custom' and mf.get('key') == 'id':
                        odoo_id_in_shopify = str(mf.get('value', ''))
                        break

                if odoo_id_in_shopify != str(odoo_partner.id):
                    # Different Odoo partner — not our duplicate, leave it
                    _logger.info(
                        "Duplicate cleanup: Shopify ID %s has different Odoo ID (%s vs %s) — skipping.",
                        c['id'], odoo_id_in_shopify, odoo_partner.id,
                    )
                    continue

                # Confirmed duplicate — same Odoo ID → delete
                del_resp = session.delete(
                    f"https://{shop_url}/admin/api/2024-01/customers/{c['id']}.json",
                    timeout=30,
                )
                if del_resp.status_code in (200, 204):
                    deleted += 1
                    _logger.info(
                        "Duplicate cleanup: deleted Shopify ID %s (Odoo partner '%s' ID %s)",
                        c['id'], odoo_partner.name, odoo_partner.id,
                    )
                else:
                    failed += 1
                    _logger.warning(
                        "Duplicate cleanup: failed to delete Shopify ID %s (%s): %s",
                        c['id'], del_resp.status_code, del_resp.text[:200],
                    )

        parts = [_("%d duplicate(s) deleted from Shopify.") % deleted]
        if failed:
            parts.append(_("%d deletion(s) failed — check logs.") % failed)
        if skipped_no_match:
            parts.append(_("%d name group(s) skipped (no Odoo match).") % skipped_no_match)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Duplicate Customer Cleanup'),
                'message': " ".join(parts),
                'type': 'warning' if (failed or skipped_no_match) else 'success',
                'sticky': True,
            },
        }

    def action_reconcile_export_log(self):
        """Delegate to res.partner — marks CSV error rows as success where the
        partner is now unblocked, exported, and has a Shopify customer ID."""
        return self.env['res.partner'].action_reconcile_export_log()


    def action_prefix_customer_emails_stg(self):
        """Prepend 'stg.' to every Shopify customer email that doesn't already have it."""
        self.ensure_one()
        shop_url = (self.shop_url or "").replace('https://', '').replace('http://', '').strip('/')

        session = requests.Session()
        session.headers.update({
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        })

        def _put_with_retry(url, payload):
            for attempt in range(5):
                resp = session.put(url, data=json.dumps(payload), timeout=30)
                if resp.status_code == 429:
                    wait = int(resp.headers.get('Retry-After', 2))
                    _logger.warning("Shopify rate limit hit — sleeping %ss", wait)
                    time.sleep(wait)
                    continue
                return resp
            return resp

        # ── 1. Fetch all customers (paginated) ────────────────────────────────
        customers = []
        url = f"https://{shop_url}/admin/api/2024-01/customers.json"
        params = {"fields": "id,email", "limit": 250}

        while url:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                time.sleep(int(resp.headers.get('Retry-After', 2)))
                continue
            if resp.status_code != 200:
                raise UserError(_("Failed to fetch customers: %s %s") % (resp.status_code, resp.text[:300]))
            customers.extend(resp.json().get("customers", []))
            url = None
            params = {}
            for part in resp.headers.get("Link", "").split(","):
                if 'rel="next"' in part:
                    url = part.strip().split(";")[0].strip().lstrip("<").rstrip(">")
                    break

        # ── 2. Update emails ──────────────────────────────────────────────────
        updated = skipped = failed = 0

        for c in customers:
            email = (c.get("email") or "").strip()
            if not email or email.lower().startswith("stg."):
                skipped += 1
                continue

            new_email = "stg." + email
            resp = _put_with_retry(
                f"https://{shop_url}/admin/api/2024-01/customers/{c['id']}.json",
                {"customer": {"id": c["id"], "email": new_email}},
            )
            if resp.status_code == 200:
                updated += 1
                _logger.info("STG email prefix: %s → %s", email, new_email)
            else:
                failed += 1
                _logger.warning("STG email prefix failed for ID %s (%s): %s",
                                c["id"], resp.status_code, resp.text[:200])

        parts = [_("%d customer email(s) updated with 'stg.' prefix.") % updated]
        if skipped:
            parts.append(_("%d already prefixed or no email — skipped.") % skipped)
        if failed:
            parts.append(_("%d update(s) failed — check server logs.") % failed)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('STG Email Prefix'),
                'message': " ".join(parts),
                'type': 'warning' if failed else 'success',
                'sticky': True,
            },
        }

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
