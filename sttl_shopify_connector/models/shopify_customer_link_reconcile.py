import csv
import os
import re
import time
import logging
import requests
from datetime import datetime

from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)
API = "2024-01"


def _normalize_name(name):
    """Case/camelCase-insensitive, whitespace-normalized comparison key."""
    return re.sub(r'\s+', ' ', (name or '').strip()).lower()


class ShopifyInstance(models.Model):
    _inherit = 'shopify.instance'

    def action_link_existing_shopify_customers(self):
        """One-time reconciliation for customers that were pushed to Shopify
        outside of this connector (e.g. via a Klaviyo export) and therefore
        have no shopify_customer_id in Odoo / custom.id metafield in Shopify.

        For each unlinked Odoo customer (same population the scheduled export
        cron uses):
        - Skip (and log) if the email belongs to more than one Odoo customer
          — we can't safely know which one the Shopify record matches.
        - Search Shopify by email. If found and the full name matches
          (case-insensitive, whitespace-normalized), link both sides:
            Odoo    -> shopify_customer_id + is_exported_to_shopify = True
            Shopify -> custom.id metafield = Odoo partner id
        - If the email is found on Shopify but the name doesn't match, skip
          and log it.
        - If the email isn't found on Shopify at all, skip silently (nothing
          to reconcile).

        Writes to a dedicated log file, separate from the regular
        product/customer export logs.
        """
        self.ensure_one()
        shop_url = (self.shop_url or "").replace('https://', '').replace('http://', '').strip('/')
        session = self._make_link_session()

        candidates = self.env['res.partner'].search([
            ('customer_rank', '>', 0),
            ('parent_id', '=', False),
            ('is_exported_to_shopify', '=', False),
            ('shopify_customer_id', '=', False),
            ('cant_export_to_shopify', '=', False),
            ('email', '!=', False),
            ('email', '!=', ''),
        ])

        by_email = {}
        for partner in candidates:
            email = (partner.email or '').strip().lower()
            if email:
                by_email.setdefault(email, []).append(partner)

        linked = 0
        log_rows = []

        for email, partners in by_email.items():
            resp = self._link_request(
                session, 'GET',
                f"https://{shop_url}/admin/api/{API}/customers/search.json",
                params={"query": f"email:{email}", "fields": "id,first_name,last_name,email"},
            )
            if resp.status_code != 200:
                log_rows.append(self._link_log_row(
                    email, 'shopify_search_failed', self._partners_label(partners), '',
                    f"Status {resp.status_code}: {resp.text[:200]}",
                ))
                _logger.warning(
                    "Shopify link: search failed for '%s': %s", email, resp.text[:200],
                )
                continue

            shopify_customers = resp.json().get('customers', [])
            if not shopify_customers:
                continue  # Not on Shopify at all — nothing to reconcile.

            sc = shopify_customers[0]
            shopify_name = f"{(sc.get('first_name') or '').strip()} {(sc.get('last_name') or '').strip()}".strip()

            # Among the Odoo customer(s) sharing this email, find the one(s)
            # whose name matches the Shopify record. Normally there's one
            # candidate; for a duplicate email in Odoo, this picks the right
            # one out of the group instead of skipping the whole group.
            matches = [p for p in partners if _normalize_name(p.name) == _normalize_name(shopify_name)]

            if len(matches) != 1:
                if len(partners) == 1:
                    reason = 'skipped_name_mismatch'
                elif len(matches) == 0:
                    reason = 'skipped_duplicate_email_in_odoo'
                else:
                    reason = 'skipped_duplicate_email_ambiguous'  # >1 Odoo customer matches both email and name
                log_rows.append(self._link_log_row(
                    email, reason, self._partners_label(partners), shopify_name,
                    _("%s Odoo customer(s) share this email, %s name match(es) against Shopify.")
                    % (len(partners), len(matches)),
                ))
                _logger.info(
                    "Shopify link: %s for '%s' — %d Odoo customer(s), %d name match(es).",
                    reason, email, len(partners), len(matches),
                )
                continue

            partner = matches[0]
            others = [p for p in partners if p.id != partner.id]

            try:
                partner._write_shopify_sync({
                    'shopify_customer_id': str(sc['id']),
                    'is_exported_to_shopify': True,
                })
                self._push_customer_id_metafield(session, shop_url, sc['id'], partner.id)
                linked += 1
                log_rows.append(self._link_log_row(
                    email, 'linked', self._partners_label([partner]), shopify_name,
                    f"Shopify Customer ID {sc['id']}"
                    + (_(" (resolved from a duplicate email shared with: %s)") % self._partners_label(others) if others else ""),
                ))
                _logger.info(
                    "Shopify link: linked '%s' (Odoo ID %s) -> Shopify ID %s.",
                    partner.name, partner.id, sc['id'],
                )
                if others:
                    log_rows.append(self._link_log_row(
                        email, 'skipped_name_mismatch', self._partners_label(others), shopify_name,
                        _("Email shared with linked customer '%s' (ID %s); name did not match.") % (partner.name, partner.id),
                    ))
            except Exception as e:
                log_rows.append(self._link_log_row(
                    email, 'link_failed', self._partners_label([partner]), shopify_name, str(e)[:300],
                ))
                _logger.warning(
                    "Shopify link: failed to link '%s': %s", partner.name, e, exc_info=True,
                )

        self._write_link_log(log_rows)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Customer Linking'),
                'message': _('%s customer(s) linked. %s row(s) written to the reconcile log.') % (linked, len(log_rows)),
                'type': 'success' if linked else 'warning',
                'sticky': True,
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Shopify HTTP (rate-limit aware)
    # ─────────────────────────────────────────────────────────────────────────

    def _make_link_session(self):
        session = requests.Session()
        session.headers.update({
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        })
        return session

    @staticmethod
    def _link_request(session, method, url, retries=3, **kwargs):
        """Shopify call with 429 retry, throttled to stay under 2 calls/sec."""
        resp = None
        for attempt in range(retries):
            resp = session.request(method, url, timeout=kwargs.pop('timeout', 15), **kwargs)
            if resp.status_code == 429:
                wait = int(resp.headers.get('Retry-After', 2)) + 1
                time.sleep(wait)
                continue
            time.sleep(0.6)
            return resp
        return resp

    def _push_customer_id_metafield(self, session, shop_url, shopify_customer_id, odoo_partner_id):
        """Set custom.id on the Shopify customer so it points back at the Odoo partner."""
        resp = self._link_request(
            session, 'POST',
            f"https://{shop_url}/admin/api/{API}/graphql.json",
            json={
                "query": "mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $metafields) { userErrors { field message code } } }",
                "variables": {"metafields": [{
                    "ownerId": f"gid://shopify/Customer/{shopify_customer_id}",
                    "namespace": "custom",
                    "key": "id",
                    "value": str(odoo_partner_id),
                    "type": "single_line_text_field",
                }]},
            },
        )
        if resp.status_code != 200:
            raise UserError(
                _("Failed to set custom.id metafield on Shopify customer %s: %s")
                % (shopify_customer_id, resp.text[:300])
            )
        errors = resp.json().get('data', {}).get('metafieldsSet', {}).get('userErrors', [])
        if errors:
            raise UserError(
                _("Shopify metafield error for customer %s: %s") % (shopify_customer_id, errors)
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _partners_label(partners):
        return "; ".join(f"{p.name} (ID {p.id})" for p in partners)

    @staticmethod
    def _link_log_row(email, result, odoo_customers, shopify_name, details):
        return {
            'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Email': email,
            'Result': result,
            'Odoo Customers': odoo_customers,
            'Shopify Name': shopify_name,
            'Details': details,
        }

    @staticmethod
    def _write_link_log(rows):
        if not rows:
            return
        log_dir = os.path.join(config.get('data_dir', '/tmp'), 'shopify_logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'customer_link_reconcile.csv')
        file_exists = os.path.isfile(log_file)
        fieldnames = ['Date', 'Email', 'Result', 'Odoo Customers', 'Shopify Name', 'Details']
        with open(log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)
