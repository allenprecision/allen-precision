from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import config
import requests
import json
import re
import csv
import os
import logging
from html import unescape
from datetime import datetime

_logger = logging.getLogger(__name__)
API = "2024-01"


# shopify_key -> odoo_field  (text / relational fields)
CUSTOMER_METAFIELD_MAP = {
    'customer_number':  'ref',
    'customer_code':    'customer_code',
    'contact_type':     'contact_type',
    'contact_1':        'contact_1',
    'contact_2':        'contact_2',
    'notes':            'comment',
    'buyer':            'buyer_id',
    'fiscal_position':  'property_account_position_id',
    'delivery_method':  'property_delivery_carrier_id',
    'pricelist':        'property_product_pricelist',
    'payment_terms':    'property_payment_term_id',
    'salesteam':        'team_id',
    'salesperson':      'user_id',
    'website_link':     'website',
    'industry':         'industry_id',
    'tax_id':           'vat',
    'address_type':     'type',
}

# Boolean Odoo fields -> Shopify metafield keys
CUSTOMER_BOOL_MAP = {
    'is_a_company':  'is_company',
    'is_tax_exempt': 'is_tax_exempt',
}

# Shopify metafield keys that must use multi_line_text_field
CUSTOMER_MULTILINE_KEYS = {'notes', 'payment_terms'}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    shopify_customer_id = fields.Char(string='Shopify Customer ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)
    cant_export_to_shopify = fields.Boolean(string='Cannot Export to Shopify', default=False, copy=False,
                                            help="Set automatically when another customer with the same email is already exported to Shopify.")

    # ─────────────────────────────────────────────────────────────────────────
    # Public actions
    # ─────────────────────────────────────────────────────────────────────────

    def action_export_to_shopify(self):
        # Only process top-level customers
        customers = self.filtered(lambda p: p.customer_rank > 0 and not p.parent_id)
        not_customer = len(self) - len(customers)

        # Skip blocked customers
        blocked = customers.filtered(lambda p: p.cant_export_to_shopify)
        customers = customers - blocked

        success_count = 0
        error_messages = []

        for partner in customers:
            instance = None
            try:
                instance = partner._resolve_instance()
                session = self._make_session(instance)
                partner._export_to_shopify(session, instance)
                partner._write_export_log('success', instance)
                success_count += 1
            except Exception as e:
                partner.write({'cant_export_to_shopify': True})
                partner._write_export_log('error', instance, str(e))
                error_messages.append(f"{partner.name}: {partner._simple_error(e)}")
                _logger.warning("Shopify customer export failed for '%s': %s", partner.name, e, exc_info=True)

        error_count = len(error_messages)
        message = _("%s customer(s) synced to Shopify.") % success_count
        if blocked:
            message += _("\n%s blocked from export (Cannot Export to Shopify is set).") % len(blocked)
        if not_customer:
            message += _("\n%s record(s) skipped — not a customer.") % not_customer
        if error_count:
            message += _("\n%s failed:\n%s") % (error_count, "\n".join(error_messages[:5]))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Customer Sync'),
                'message': message,
                'type': 'warning' if (error_count or blocked or not_customer) else 'success',
                'sticky': bool(error_count),
            },
        }

    _VALID_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

    @api.model
    def action_recover_blocked_customers(self):
        """Cron: resolve cant_export_to_shopify customers blocked by 'email already taken'.

        For each blocked customer (no shopify_customer_id):
        1. If email format is invalid → leave blocked (Shopify will reject it anyway).
        2. If another Odoo partner shares the same email → skip (real duplicate).
        3. Otherwise search Shopify by email. If a customer with the same name+email
           exists, store their Shopify ID and clear the blocked flag.
        4. If not found on Shopify at all → unblock for re-export.
        """
        self = self.with_context(auditlog_disabled=True, tracking_disable=True, no_recompute=True)

        instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
        if not instances:
            return

        blocked = self.env['res.partner'].search([
            ('cant_export_to_shopify', '=', True),
            ('shopify_customer_id', '=', False),
            ('email', '!=', False),
            ('email', '!=', ''),
        ], limit=50, order='id desc')

        if not blocked:
            return

        instance = instances[0]
        session = self._make_session(instance)
        shop_url = (instance.shop_url or "").replace('https://', '').replace('http://', '').strip('/')

        recovered = skipped_odoo_dup = not_found = 0

        skipped_invalid_email = 0

        for partner in blocked:
            email = (partner.email or "").strip().lower()

            # ── 1. Validate email format ──────────────────────────────────────
            if not self._VALID_EMAIL_RE.match(email):
                skipped_invalid_email += 1
                _logger.info(
                    "Blocked customer '%s': email '%s' has invalid format — staying blocked.",
                    partner.name, email,
                )
                continue

            # ── 2. Check for duplicate email in Odoo ──────────────────────────
            odoo_dup = self.env['res.partner'].search([
                ('email', '=ilike', email),
                ('id', '!=', partner.id),
            ], limit=1)
            if odoo_dup:
                skipped_odoo_dup += 1
                _logger.info(
                    "Blocked customer '%s': email '%s' also on Odoo partner '%s' — skipping.",
                    partner.name, email, odoo_dup.name,
                )
                continue

            # ── 2. Search Shopify by email ────────────────────────────────────
            resp = session.get(
                f"https://{shop_url}/admin/api/{API}/customers/search.json",
                params={"query": f"email:{email}", "fields": "id,first_name,last_name,email"},
                timeout=15,
            )
            if resp.status_code != 200:
                _logger.warning(
                    "Shopify customer search failed for '%s': %s", partner.name, resp.text[:200]
                )
                continue

            partner_full_name = (partner.name or "").strip().lower()
            matched = None
            for sc in resp.json().get("customers", []):
                shopify_name = (
                    f"{(sc.get('first_name') or '').strip()} {(sc.get('last_name') or '').strip()}".strip().lower()
                )
                if shopify_name == partner_full_name:
                    matched = sc
                    break

            if not matched:
                # Email not on Shopify at all — unblock so the next scheduled
                # export can create the customer fresh.
                partner._write_shopify_sync({'cant_export_to_shopify': False})
                not_found += 1
                _logger.info(
                    "Blocked customer '%s': email '%s' not found on Shopify — unblocked for re-export.",
                    partner.name, email,
                )
                continue

            # ── 3. Store Shopify ID and clear blocked flags ───────────────────
            partner._write_shopify_sync({
                'shopify_customer_id':    str(matched['id']),
                'is_exported_to_shopify': True,
                'cant_export_to_shopify': False,
            })
            recovered += 1
            _logger.info("Recovered blocked customer '%s' → Shopify ID %s", partner.name, matched['id'])

        _logger.info(
            "Shopify recover blocked customers: %s recovered, %s skipped (Odoo duplicate), "
            "%s unblocked (not on Shopify), %s skipped (invalid email format).",
            recovered, skipped_odoo_dup, not_found, skipped_invalid_email,
        )

    @api.model
    def action_scheduled_export_to_shopify(self):
        """Scheduled action — exports opted-in customers, 50 per run, safe for parallel runs."""
        self = self.with_context(auditlog_disabled=True, tracking_disable=True, no_recompute=True)

        instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
        if not instances:
            _logger.warning("Shopify scheduled customer export: no confirmed instance.")
            return

        customers = self.env['res.partner'].search([
            ('customer_rank', '>', 0),
            ('parent_id', '=', False),
            ('is_exported_to_shopify', '=', False),
            ('shopify_customer_id', '=', False),
            ('cant_export_to_shopify', '=', False),
        ], limit=50)

        if not customers:
            return

        # Lock rows to prevent parallel cron runs processing the same customers
        self.env.cr.execute(
            'SELECT id FROM res_partner WHERE id = ANY(%s) FOR UPDATE SKIP LOCKED',
            (list(customers.ids),),
        )
        locked_ids = {r[0] for r in self.env.cr.fetchall()}
        customers = customers.filtered(lambda p: p.id in locked_ids)
        if not customers:
            return

        if len(instances) == 1:
            customers.filtered(lambda p: not p.shopify_instance_id).write(
                {'shopify_instance_id': instances[0].id}
            )

        by_instance = {}
        for p in customers:
            if p.shopify_instance_id:
                by_instance.setdefault(p.shopify_instance_id, []).append(p)

        success = failed = 0
        for instance, group in by_instance.items():
            session = self._make_session(instance)
            for partner in group:
                try:
                    with self.env.cr.savepoint():
                        partner._export_to_shopify(session, instance)
                    partner._write_export_log('success', instance)
                    success += 1
                except Exception as e:
                    partner.write({'cant_export_to_shopify': True})
                    partner._write_export_log('error', instance, str(e))
                    failed += 1
                    _logger.warning(
                        "Shopify scheduled customer export: failed '%s' (ID %s): %s",
                        partner.name, partner.id, e, exc_info=True,
                    )

        _logger.info("Shopify scheduled customer export: %s succeeded, %s failed.", success, failed)

    # ─────────────────────────────────────────────────────────────────────────
    # Core export
    # ─────────────────────────────────────────────────────────────────────────

    def _export_to_shopify(self, session, instance):
        self.ensure_one()

        if not self.customer_rank:
            raise UserError(_("'%s' is not a customer and cannot be exported to Shopify.") % self.name)

        shop_url = (instance.shop_url or "").replace('https://', '').replace('http://', '').strip('/')

        # ── 404 guard: clear stale ID ─────────────────────────────────────────
        if self.shopify_customer_id:
            check = session.get(
                f"https://{shop_url}/admin/api/{API}/customers/{self.shopify_customer_id}.json",
                timeout=10,
            )
            if check.status_code == 404:
                self._write_shopify_sync({'shopify_customer_id': False})

        # ── Build payload ─────────────────────────────────────────────────────
        first_name, last_name = self._split_name(self)
        phone = self._normalize_phone(self.phone or self.mobile or "", self)

        payload = {
            "customer": {
                "first_name": first_name,
                "last_name":  last_name,
                "email":      self.email or "",
                "phone":      phone,
                "addresses":  self._build_addresses(),
                "metafields": self._build_metafields(),
            }
        }

        # ── Send ──────────────────────────────────────────────────────────────
        resp = self._send(session, shop_url, payload)

        # Phone 422 retry — strip phone and retry
        if resp.status_code == 422 and 'phone' in resp.text:
            payload["customer"].pop("phone", None)
            for addr in payload["customer"].get("addresses", []):
                addr.pop("phone", None)
            resp = self._send(session, shop_url, payload)

        if resp.status_code not in (200, 201):
            raise UserError(
                _("Shopify export failed for '%s'. Status %s:\n%s")
                % (self.name, resp.status_code, resp.text[:500])
            )

        customer = resp.json().get('customer', {})
        self._write_shopify_sync({
            'shopify_customer_id': str(customer.get('id', '')),
            'is_exported_to_shopify': True,
        })

    # ─────────────────────────────────────────────────────────────────────────
    # HTTP helper
    # ─────────────────────────────────────────────────────────────────────────

    def _send(self, session, shop_url, payload):
        base = f"https://{shop_url}/admin/api/{API}/customers"
        if self.shopify_customer_id:
            resp = session.put(
                f"{base}/{self.shopify_customer_id}.json",
                data=json.dumps(payload), timeout=15,
            )
            _logger.info("Shopify customer PUT '%s' → %s", self.name, resp.status_code)
        else:
            resp = session.post(f"{base}.json", data=json.dumps(payload), timeout=15)
            _logger.info("Shopify customer POST '%s' → %s", self.name, resp.status_code)
        return resp

    # ─────────────────────────────────────────────────────────────────────────
    # Address builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_addresses(self):
        """Build address list for Shopify.

        Main partner address is always default=True.
        Child addresses (delivery, invoice, other, contact with data) are included
        as additional non-default addresses.
        """
        children = self.child_ids.filtered(
            lambda c: c.type in ('delivery', 'invoice', 'other', 'contact')
        )

        addresses = []

        # Main customer address — always default
        main = self._address_dict(self)
        main['default'] = True
        addresses.append(main)

        # Child addresses — never default
        for child in children:
            addr = self._address_dict(child)
            if not any([addr['address1'], addr['city'], addr['zip']]):
                continue
            addr['default'] = False
            addresses.append(addr)

        return addresses

    def _address_dict(self, partner):
        first_name, last_name = self._split_name(partner)
        phone = self._normalize_phone(partner.phone or partner.mobile or "", partner)
        return {
            "address1":   partner.street or "",
            "address2":   partner.street2 or "",
            "city":       partner.city or "",
            "province":   partner.state_id.name if partner.state_id else "",
            "zip":        partner.zip or "",
            "country":    partner.country_id.name if partner.country_id else "",
            "first_name": first_name,
            "last_name":  last_name,
            "phone":      phone,
        }

    @staticmethod
    def _normalize_phone(phone, partner):
        """Normalize phone to E.164 format (+<country_code><digits>).
        Shopify requires E.164; without it the number displays without formatting."""
        if not phone:
            return ""
        digits = re.sub(r'[^\d]', '', phone)
        if not digits:
            return ""
        if phone.strip().startswith('+'):
            return '+' + digits
        # Prepend country dialing code from partner's country
        if partner.country_id and partner.country_id.phone_code:
            return f"+{partner.country_id.phone_code}{digits}"
        return digits

    # ─────────────────────────────────────────────────────────────────────────
    # Metafields
    # ─────────────────────────────────────────────────────────────────────────

    def _build_metafields(self):
        mfs = [
            {
                "namespace": "custom",
                "key":       "id",
                "value":     str(self.id),
                "type":      "single_line_text_field",
            }
        ]

        # Text / relational fields
        for shopify_key, odoo_field in CUSTOMER_METAFIELD_MAP.items():
            val = getattr(self, odoo_field, None)
            if not val:
                continue
            field_def = self._fields.get(odoo_field)
            if field_def:
                if field_def.type == 'many2one':
                    val = val.display_name or val.name
                elif field_def.type == 'selection':
                    val = dict(field_def._description_selection(self.env)).get(val, val)
                elif field_def.type in ('html', 'text'):
                    val = unescape(re.sub(r"<[^>]+>", "", str(val))).strip()
            val = str(val).strip()
            if not val:
                continue
            mtype = "multi_line_text_field" if shopify_key in CUSTOMER_MULTILINE_KEYS else "single_line_text_field"
            mfs.append({
                "namespace": "custom",
                "key":       shopify_key,
                "value":     val,
                "type":      mtype,
            })

        # Boolean fields — send as single_line_text_field "true"/"false"
        # (Shopify metafield definitions for these are single_line_text_field)
        for shopify_key, odoo_field in CUSTOMER_BOOL_MAP.items():
            val = getattr(self, odoo_field, None)
            if val is None:
                continue
            mfs.append({
                "namespace": "custom",
                "key":       shopify_key,
                "value":     "true" if val else "false",
                "type":      "single_line_text_field",
            })

        return mfs

    # ─────────────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────────────

    def _write_export_log(self, status, instance, error_message=None):
        try:
            log_dir = os.path.join(config.get('data_dir', '/tmp'), 'shopify_logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "customer_export.csv")
            file_exists = os.path.isfile(log_file)
            with open(log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        'Export Date', 'Customer Name', 'Odoo ID',
                        'Shopify Customer ID', 'Instance', 'Status', 'Error Message',
                    ])
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    self.name,
                    self.id,
                    self.shopify_customer_id or '',
                    instance.name if instance else '',
                    status,
                    error_message or '',
                ])
        except Exception as e:
            _logger.warning("Failed to write export log for '%s': %s", self.name, e)

    @api.model
    def action_reconcile_export_log(self):
        """Reconcile + deduplicate the customer export CSV against live Odoo state.

        For each Odoo ID:
        - exported + has shopify_id + not blocked  → success
        - blocked or not exported                  → error
        - Keep only one row per Odoo ID (latest Export Date as tiebreaker).
        """
        log_file = os.path.join(config.get('data_dir', '/tmp'), 'shopify_logs', 'customer_export.csv')
        if not os.path.isfile(log_file):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Reconcile Export Log'),
                    'message': _('Log file not found: %s') % log_file,
                    'type': 'warning', 'sticky': False,
                },
            }

        to_success = to_error = 0
        try:
            with open(log_file, 'r', newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))

            # ── Step 1: deduplicate — one row per Odoo ID ────────────────────
            # Keep latest row by date. Also preserve the most recent error
            # message across all rows so it isn't lost if a success row wins.
            best = {}        # oid -> latest row
            best_err_msg = {}  # oid -> most recent error message

            for row in rows:
                oid = row.get('Odoo ID', '')
                if not oid:
                    continue
                # Track latest error message for this ID
                if row.get('Status') == 'error' and row.get('Error Message', '').strip():
                    existing_err_date = best_err_msg.get(oid, ('', ''))[0]
                    if row.get('Export Date', '') >= existing_err_date:
                        best_err_msg[oid] = (row.get('Export Date', ''), row['Error Message'])
                # Keep latest row overall
                existing = best.get(oid)
                if existing is None or row.get('Export Date', '') > existing.get('Export Date', ''):
                    best[oid] = row

            deduped_rows = list(best.values())
            removed = len(rows) - len(deduped_rows)

            # ── Step 2: reconcile every row against live Odoo state ───────────
            for row in deduped_rows:
                try:
                    partner_id = int(row.get('Odoo ID', 0))
                except (ValueError, TypeError):
                    continue
                partner = self.env['res.partner'].browse(partner_id).exists()
                if not partner:
                    continue

                is_exported = (
                    partner.is_exported_to_shopify
                    and partner.shopify_customer_id
                    and not partner.cant_export_to_shopify
                )
                oid = row.get('Odoo ID', '')
                if is_exported and row['Status'] != 'success':
                    row['Status'] = 'success'
                    row['Shopify Customer ID'] = partner.shopify_customer_id
                    row['Error Message'] = ''
                    to_success += 1
                elif not is_exported and row['Status'] != 'error':
                    row['Status'] = 'error'
                    # Restore original error message if available
                    row['Error Message'] = best_err_msg.get(oid, ('', ''))[1] or ''
                    to_error += 1

            fieldnames = ['Export Date', 'Customer Name', 'Odoo ID',
                          'Shopify Customer ID', 'Instance', 'Status', 'Error Message']
            with open(log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(deduped_rows)

            _logger.info(
                "Shopify export log reconciled: %s → success, %s → error, %s duplicates removed.",
                to_success, to_error, removed,
            )
        except Exception as e:
            _logger.error("Failed to reconcile export log: %s", e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Reconcile Export Log'),
                    'message': _('Error: %s') % str(e),
                    'type': 'danger', 'sticky': True,
                },
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reconcile Export Log'),
                'message': _(
                    '%s → success, %s → error, %s duplicate rows removed.'
                ) % (to_success, to_error, removed),
                'type': 'success', 'sticky': False,
            },
        }

    def _resolve_instance(self):
        if self.shopify_instance_id:
            return self.shopify_instance_id
        instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
        if len(instances) == 1:
            self.shopify_instance_id = instances[0].id
            return instances[0]
        raise UserError(_("Please select a Shopify Instance for customer: %s") % self.name)

    @staticmethod
    def _split_name(partner):
        parts = (partner.name or "").split()
        if len(parts) <= 1:
            return partner.name or "", ""
        return " ".join(parts[:-1]), parts[-1]

    def _write_shopify_sync(self, vals):
        """Write Shopify sync fields safely — falls back to SQL in cron context."""
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
        s.headers.update({
            "X-Shopify-Access-Token": instance.access_token,
            "Content-Type": "application/json",
        })
        return s

    def _simple_error(self, error):
        text = str(error)
        if 'phone' in text and 'is invalid' in text:
            return _("Invalid phone number")
        if 'email' in text and 'has already been taken' in text:
            return _("Email already exists in Shopify")
        if 'Status: 404' in text:
            return _("Customer not found in Shopify")
        if 'Status: 401' in text or 'Status: 403' in text:
            return _("Shopify connection failed — check access token")
        if 'Please select a Shopify Instance' in text:
            return _("Shopify instance not assigned")
        return text[:300]
