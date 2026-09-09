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
EXPORT_LINKED_BATCH_SIZE = 500
DEDUP_BATCH_SIZE = 100


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
             "reconciliation action (matched by email + name) — linking only "
             "sets the Shopify ID and the custom.id metafield, it doesn't push "
             "the rest of the customer's data. Acts as a pending-export queue: "
             "'Export Reconciled Customers to Shopify' picks up everyone with "
             "this set to True, exports their full data, then clears it.",
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

            # Guard against assigning a Shopify customer that ANOTHER Odoo
            # partner already holds. This can otherwise happen across
            # separate batches: two Odoo customers can share both email and
            # name (e.g. genuine duplicate contacts), but only one of them is
            # visible as a "duplicate" within any single batch — the other
            # was already linked (and dropped out of the candidate pool) in
            # an earlier batch, so this run sees only one candidate and would
            # otherwise happily link it to the very same Shopify ID again.
            already_claimed_by = self.env['res.partner'].search([
                ('shopify_customer_id', '=', str(sc['id'])),
                ('id', '!=', partner.id),
            ], limit=1)
            if already_claimed_by:
                log_rows.append(self._link_log_row(
                    email, 'skipped_shopify_id_already_claimed', self._partners_label([partner]), shopify_name,
                    _("Shopify Customer ID %s is already linked to a different Odoo customer: '%s' (ID %s).")
                    % (sc['id'], already_claimed_by.name, already_claimed_by.id),
                ))
                _logger.info(
                    "Shopify link: '%s' (Odoo ID %s) matches Shopify ID %s, but that ID is already "
                    "claimed by Odoo partner '%s' (ID %s) — skipping to avoid a duplicate assignment.",
                    partner.name, partner.id, sc['id'], already_claimed_by.name, already_claimed_by.id,
                )
                continue

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

    def action_export_reconciled_customers(self):
        """Push full customer data to Shopify for everyone the reconciliation
        action linked (shopify_reconcile_linked = True).

        Linking only stores the Shopify ID on Odoo and sets the custom.id
        metafield on Shopify — it does not sync name, addresses, or the rest
        of the metafields. This reuses the existing, already-working
        res.partner.action_export_to_shopify() (PUT, since shopify_customer_id
        is now set) to bring the rest of the data across.

        Processes at most EXPORT_LINKED_BATCH_SIZE partners per click.
        shopify_reconcile_linked is cleared for the whole batch as it's picked
        up (regardless of individual export success/failure — failures are
        already tracked separately via cant_export_to_shopify and the existing
        recovery cron), so repeated clicks naturally work through the rest
        without needing a separate bookmark.
        """
        self.ensure_one()
        partners = self.env['res.partner'].search(
            [('shopify_reconcile_linked', '=', True)], limit=EXPORT_LINKED_BATCH_SIZE,
        )

        if not partners:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Export Reconciled Customers'),
                    'message': _('No customers pending export (none have shopify_reconcile_linked set).'),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        remaining_after_batch = self.env['res.partner'].search_count([
            ('shopify_reconcile_linked', '=', True), ('id', 'not in', partners.ids),
        ])

        partners.write({'shopify_reconcile_linked': False})
        result = partners.action_export_to_shopify()

        if isinstance(result, dict) and result.get('params'):
            extra = (
                _('\n%s more pending — click the button again to continue.') % remaining_after_batch
                if remaining_after_batch else _('\nAll pending customers processed.')
            )
            result['params']['message'] = (result['params'].get('message') or '') + extra
            result['params']['sticky'] = True
        return result

    def action_fix_duplicate_shopify_id_assignments(self):
        """One-time cleanup for a bug in action_link_existing_shopify_customers:
        because duplicate-email detection only looked within a single batch,
        two (or more) Odoo customers sharing an email+name could each get
        linked to the SAME Shopify customer across separate batch runs — the
        first batch links one, that partner then drops out of later batches'
        candidate pools (shopify_customer_id no longer blank), so a later
        batch sees the second partner as an unambiguous solo match and links
        it to the very same Shopify ID. A guard now prevents this going
        forward (see the already_claimed_by check above); this action
        repairs Odoo records already corrupted by it.

        For every Shopify Customer ID held by more than one Odoo partner:
        - Shopify's own custom.id metafield is the authoritative source of
          truth for who really owns that customer (it holds whichever
          partner's link attempt wrote it last).
        - The partner matching that metafield value is left untouched.
        - Every OTHER partner wrongly holding this Shopify ID gets:
            shopify_customer_id = False, shopify_reconcile_linked = False,
            is_exported_to_shopify = False, cant_export_to_shopify = True
          (clearing the ID, not just the flags, so a future export attempt on
          that record can never PUT into — and corrupt — the sibling's real
          Shopify customer), and a log row explaining why.
        - If Shopify's metafield doesn't match ANY partner in the group
          (unexpected), that group is left untouched and logged for manual
          review rather than guessed at.

        Processes at most DEDUP_BATCH_SIZE duplicate groups per click (one
        Shopify metafield lookup per group) — click again for the rest.
        """
        self.ensure_one()
        shop_url = (self.shop_url or "").replace('https://', '').replace('http://', '').strip('/')
        session = self._make_link_session()

        all_linked = self.env['res.partner'].search([
            ('shopify_customer_id', '!=', False), ('shopify_customer_id', '!=', ''),
        ])
        by_shopify_id = {}
        for p in all_linked:
            by_shopify_id.setdefault(p.shopify_customer_id, []).append(p)

        dup_items = [(sid, partners) for sid, partners in by_shopify_id.items() if len(partners) > 1]
        total_groups = len(dup_items)
        batch = dup_items[:DEDUP_BATCH_SIZE]
        remaining = total_groups - len(batch)

        fixed = 0
        unresolved = 0
        log_rows = []

        for sid, partners in batch:
            resp = self._link_request(
                session, 'GET',
                f"https://{shop_url}/admin/api/{API}/customers/{sid}/metafields.json",
                params={"namespace": "custom", "key": "id"},
            )
            odoo_id_on_shopify = None
            if resp.status_code == 200:
                for mf in resp.json().get('metafields', []):
                    if mf.get('namespace') == 'custom' and mf.get('key') == 'id':
                        odoo_id_on_shopify = str(mf.get('value', '')).strip()
                        break

            keep = next((p for p in partners if str(p.id) == odoo_id_on_shopify), None)
            if not keep:
                unresolved += 1
                log_rows.append(self._link_log_row(
                    '', 'dedup_unresolved', self._partners_label(partners), '',
                    _("Shopify Customer ID %s: metafield value (%r) doesn't match any partner in this "
                      "group — left untouched, needs manual review.") % (sid, odoo_id_on_shopify),
                ))
                _logger.warning(
                    "Shopify dedup: Shopify ID %s metafield=%r doesn't match any of %s — skipping.",
                    sid, odoo_id_on_shopify, self._partners_label(partners),
                )
                continue

            for loser in partners:
                if loser.id == keep.id:
                    continue
                loser._write_shopify_sync({
                    'shopify_customer_id': False,
                    'shopify_reconcile_linked': False,
                    'is_exported_to_shopify': False,
                    'cant_export_to_shopify': True,
                })
                fixed += 1
                log_rows.append(self._link_log_row(
                    '', 'dedup_cleared_duplicate_assignment', self._partners_label([loser]), '',
                    _("Shopify Customer ID %s actually belongs to Odoo customer '%s' (ID %s); "
                      "cleared this record's incorrect link to it.") % (sid, keep.name, keep.id),
                ))
                _logger.info(
                    "Shopify dedup: cleared '%s' (Odoo ID %s) — Shopify ID %s belongs to '%s' (ID %s).",
                    loser.name, loser.id, sid, keep.name, keep.id,
                )

        self._write_link_log(log_rows)

        message = _(
            '%s duplicate Shopify ID group(s) processed. %s Odoo record(s) cleared. %s group(s) unresolved.'
        ) % (len(batch), fixed, unresolved)
        if remaining:
            message += _('\n%s more group(s) left — click the button again to continue.') % remaining
        elif total_groups:
            message += _('\nThat was the last batch — all duplicate groups processed.')
        else:
            message += _('\nNo duplicate Shopify ID assignments found.')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Fix Duplicate Shopify ID Assignments'),
                'message': message,
                'type': 'warning' if unresolved else 'success',
                'sticky': True,
            },
        }

    def action_delete_genuine_duplicate_shopify_customers(self):
        """Cleanup for a DIFFERENT duplicate scenario than the one above: two
        (or more) Odoo customers sharing an email each ended up with their
        OWN, genuinely separate Shopify customer record (different Shopify
        IDs) — real duplicates on Shopify itself, not just an Odoo-side ID
        mix-up. This happens when, e.g., a Klaviyo-imported record already
        existed under one email spelling/casing and our own export created a
        second Shopify customer that didn't collide with it.

        For every Odoo email shared by 2+ exported customers who point to 2+
        DISTINCT Shopify customer IDs:
        - Read the custom.id metafield on each of those Shopify customer IDs.
        - Whichever one matches an Odoo partner ID that's actually in this
          email's Odoo group is the correct one — keep it untouched.
        - Every OTHER Shopify customer ID in the group is a genuine duplicate:
          DELETE it from Shopify, then clear the Odoo record(s) that pointed
          to it (shopify_customer_id, shopify_reconcile_linked cleared;
          is_exported_to_shopify=False, cant_export_to_shopify=True) and log
          why.
        - If no Shopify ID's metafield matches anyone in the group, the whole
          group is left untouched (nothing deleted) and logged for manual
          review — never delete on a guess.

        This is a genuine DELETE on Shopify, unlike the Odoo-only cleanup
        above — confirm on the button reflects that. Processes at most
        DEDUP_BATCH_SIZE email-groups per click.
        """
        self.ensure_one()
        shop_url = (self.shop_url or "").replace('https://', '').replace('http://', '').strip('/')
        session = self._make_link_session()

        exported = self.env['res.partner'].search([
            ('is_exported_to_shopify', '=', True),
            ('shopify_customer_id', '!=', False), ('shopify_customer_id', '!=', ''),
            ('email', '!=', False), ('email', '!=', ''),
        ])
        by_email = {}
        for p in exported:
            email = (p.email or '').strip().lower()
            if email:
                by_email.setdefault(email, []).append(p)

        dup_items = [
            (email, partners) for email, partners in by_email.items()
            if len({p.shopify_customer_id for p in partners}) > 1
        ]
        total_groups = len(dup_items)
        batch = dup_items[:DEDUP_BATCH_SIZE]
        remaining = total_groups - len(batch)

        deleted = 0
        unresolved = 0
        log_rows = []

        for email, partners in batch:
            ids_in_group = {str(p.id) for p in partners}
            distinct_shopify_ids = sorted({p.shopify_customer_id for p in partners})

            keep_shopify_id = None
            for sid in distinct_shopify_ids:
                resp = self._link_request(
                    session, 'GET',
                    f"https://{shop_url}/admin/api/{API}/customers/{sid}/metafields.json",
                    params={"namespace": "custom", "key": "id"},
                )
                if resp.status_code != 200:
                    continue
                for mf in resp.json().get('metafields', []):
                    if mf.get('namespace') == 'custom' and mf.get('key') == 'id':
                        if str(mf.get('value', '')).strip() in ids_in_group:
                            keep_shopify_id = sid
                        break
                if keep_shopify_id:
                    break

            if not keep_shopify_id:
                unresolved += 1
                log_rows.append(self._link_log_row(
                    email, 'genuine_dup_unresolved', self._partners_label(partners), '',
                    _("%s distinct Shopify customer IDs for this email, none of their metafields "
                      "matched an Odoo customer in this group — left untouched, needs manual review.")
                    % len(distinct_shopify_ids),
                ))
                continue

            for sid in distinct_shopify_ids:
                if sid == keep_shopify_id:
                    continue
                del_resp = self._link_request(
                    session, 'DELETE', f"https://{shop_url}/admin/api/{API}/customers/{sid}.json",
                )
                if del_resp.status_code not in (200, 204):
                    log_rows.append(self._link_log_row(
                        email, 'genuine_dup_delete_failed', '', '',
                        _("Failed to delete duplicate Shopify customer %s: %s %s")
                        % (sid, del_resp.status_code, del_resp.text[:200]),
                    ))
                    _logger.warning("Shopify genuine-dup cleanup: failed to delete %s: %s", sid, del_resp.text[:200])
                    continue

                deleted += 1
                affected = [p for p in partners if p.shopify_customer_id == sid]
                for p in affected:
                    p._write_shopify_sync({
                        'shopify_customer_id': False,
                        'shopify_reconcile_linked': False,
                        'is_exported_to_shopify': False,
                        'cant_export_to_shopify': True,
                    })
                log_rows.append(self._link_log_row(
                    email, 'genuine_dup_deleted', self._partners_label(affected), '',
                    _("Deleted duplicate Shopify customer %s (kept %s); cleared the Odoo record(s) that pointed to it.")
                    % (sid, keep_shopify_id),
                ))
                _logger.info(
                    "Shopify genuine-dup cleanup: deleted %s (kept %s) for email '%s'; cleared %s.",
                    sid, keep_shopify_id, email, self._partners_label(affected),
                )

        self._write_link_log(log_rows)

        message = _(
            '%s email group(s) processed. %s duplicate Shopify customer(s) deleted. %s group(s) unresolved.'
        ) % (len(batch), deleted, unresolved)
        if remaining:
            message += _('\n%s more group(s) left — click the button again to continue.') % remaining
        elif total_groups:
            message += _('\nThat was the last batch — all groups processed.')
        else:
            message += _('\nNo genuine duplicate Shopify customers found.')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Delete Genuine Duplicate Shopify Customers'),
                'message': message,
                'type': 'warning' if unresolved else 'success',
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
