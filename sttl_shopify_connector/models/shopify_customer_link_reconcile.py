import csv
import os
import re
import time
import logging
import requests
from datetime import datetime

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)
API = "2024-01"
LINK_BATCH_SIZE = 1000


def _normalize_name(name):
    """Case/camelCase-insensitive, whitespace-normalized comparison key."""
    return re.sub(r'\s+', ' ', (name or '').strip()).lower()


def _strip_std_prefix(email):
    """These Shopify customers were imported with a literal 'std' prefix
    stuck onto every email (e.g. 'stdjohn@example.com' for 'john@example.com').
    Strip it before matching against Odoo emails."""
    email = (email or '').strip().lower()
    if email.startswith('std'):
        email = email[3:]
    return email


class ResPartner(models.Model):
    _inherit = 'res.partner'

    shopify_reconcile_linked = fields.Boolean(
        string='Linked via Shopify Reconcile',
        default=False,
        copy=False,
        help="Set to True when this customer was linked to an already-existing "
             "Shopify customer by the 'Link Existing Shopify Customers' "
             "reconciliation action (matched by email + name), as opposed to "
             "being freshly exported by the normal export flow. Lets you filter "
             "for what that action has already handled.",
    )


class ShopifyInstance(models.Model):
    _inherit = 'shopify.instance'

    shopify_link_reconcile_last_id = fields.Integer(
        string='Link Reconcile: Last Processed Partner ID',
        default=0,
        help="Bookmark for 'Link Existing Shopify Customers' — batches process "
             f"{LINK_BATCH_SIZE} Odoo customers per click (ordered by ID) and advance "
             "this automatically, so repeated clicks continue instead of "
             "reprocessing the same batch. Reset to 0 to start over from the beginning.",
    )

    def action_link_existing_shopify_customers(self):
        """One-time reconciliation for customers that were pushed to Shopify
        outside of this connector (e.g. via a Klaviyo export) and therefore
        have no shopify_customer_id in Odoo / custom.id metafield in Shopify.

        For each unlinked Odoo customer (same population the scheduled export
        cron uses):
        - Skip (and log) if the email belongs to more than one Odoo customer
          and no single one of them matches the Shopify name.
        - If the full name matches (case-insensitive, whitespace-normalized)
          the Shopify record for that email, link both sides:
            Odoo    -> shopify_customer_id + is_exported_to_shopify = True
            Shopify -> custom.id metafield = Odoo partner id
        - If the email is found on Shopify but the name doesn't match, skip
          and log it.
        - If the email isn't found on Shopify at all, skip silently (nothing
          to reconcile).

        All Shopify customers are fetched once in bulk (paginated) and
        indexed by email up front — matching is then done in memory instead
        of one Shopify search call per Odoo candidate, which is what made
        earlier per-customer search calls slow on large customer lists.

        Processes at most LINK_BATCH_SIZE Odoo customers per call (ordered by
        id, resuming from shopify_link_reconcile_last_id) so a single click
        can't run long enough to time out the connection on large customer
        lists — click the button repeatedly to work through the rest; the
        bookmark advances automatically each time.

        Writes to a dedicated log file, separate from the regular
        product/customer export logs.
        """
        self.ensure_one()
        shop_url = (self.shop_url or "").replace('https://', '').replace('http://', '').strip('/')
        session = self._make_link_session()

        # Deliberately NOT filtering on is_exported_to_shopify / cant_export_to_shopify
        # here (unlike the scheduled export cron) — customers already blocked or
        # marked exported may still have no shopify_customer_id, and those are
        # exactly the ones this reconciliation needs to catch. Only real
        # exclusion: already linked (shopify_customer_id already set).
        base_domain = [
            ('customer_rank', '>', 0),
            ('parent_id', '=', False),
            ('shopify_customer_id', '=', False),
            ('email', '!=', False),
            ('email', '!=', ''),
        ]
        candidates = self.env['res.partner'].search(
            base_domain + [('id', '>', self.shopify_link_reconcile_last_id)],
            order='id asc', limit=LINK_BATCH_SIZE,
        )
        remaining_after_batch = self.env['res.partner'].search_count(
            base_domain + [('id', '>', max(candidates.ids, default=self.shopify_link_reconcile_last_id))]
        )

        by_email = {}
        for partner in candidates:
            email = (partner.email or '').strip().lower()
            if email:
                by_email.setdefault(email, []).append(partner)

        shopify_by_email, shopify_raw_count, shopify_no_email_count = self._fetch_all_shopify_customers_by_email(
            session, shop_url
        )

        linked = 0
        log_rows = []

        for email, partners in by_email.items():
            shopify_customers = shopify_by_email.get(email, [])
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
                    'shopify_reconcile_linked': True,
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

        if candidates:
            self.write({'shopify_link_reconcile_last_id': max(candidates.ids)})

        message = _(
            'Batch done: %s Odoo candidate(s) checked (%s distinct emails). Shopify returned %s customer(s) '
            '(%s had no email — likely missing protected-customer-data access) '
            '(%s usable by email). %s linked. %s row(s) written to the reconcile log.'
        ) % (
            len(candidates), len(by_email), shopify_raw_count, shopify_no_email_count,
            sum(len(v) for v in shopify_by_email.values()), linked, len(log_rows),
        )
        if remaining_after_batch:
            message += _('\n%s more Odoo customer(s) left — click the button again to continue.') % remaining_after_batch
        elif candidates:
            message += _('\nThat was the last batch — all candidates processed.')
        else:
            message += _('\nNo candidates found from this bookmark onward. '
                          'Reset "Link Reconcile: Last Processed Partner ID" to 0 to start over.')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Customer Linking'),
                'message': message,
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

    def _fetch_all_shopify_customers_by_email(self, session, shop_url, max_customers=None):
        """Bulk-fetch Shopify customers (paginated, 250/page) and index by
        lowercased email. One-time cost of a handful of calls instead of one
        Shopify search request per Odoo candidate — that per-record search is
        what made this slow on stores with many customers.

        max_customers caps how many Shopify customers are pulled in total —
        used for quick, small-batch testing instead of fetching the whole
        store.

        Returns (by_email, raw_count, no_email_count) so the caller can tell
        apart "Shopify returned nothing at all" from "Shopify returned
        customers but they had no email" (e.g. protected-customer-data
        access not granted, which makes Shopify silently redact/omit fields
        instead of erroring)."""
        by_email = {}
        total = 0
        no_email = 0
        url = f"https://{shop_url}/admin/api/{API}/customers.json"
        page_limit = min(250, max_customers) if max_customers else 250
        params = {"fields": "id,first_name,last_name,email", "limit": page_limit}

        while url:
            resp = self._link_request(session, 'GET', url, params=params)
            if resp.status_code != 200:
                raise UserError(
                    _("Failed to fetch Shopify customers: %s %s") % (resp.status_code, resp.text[:300])
                )
            for c in resp.json().get('customers', []):
                email = _strip_std_prefix(c.get('email'))
                total += 1
                if email:
                    by_email.setdefault(email, []).append(c)
                else:
                    no_email += 1
                if max_customers and total >= max_customers:
                    return by_email, total, no_email
            url = None
            params = {}
            for part in resp.headers.get('Link', '').split(','):
                if 'rel="next"' in part:
                    url = part.strip().split(';')[0].strip().lstrip('<').rstrip('>')
                    break

        return by_email, total, no_email

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
