from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import re
import logging
import os
import csv
from datetime import datetime
from odoo.tools import config, html2plaintext

_logger = logging.getLogger(__name__)
API = "2024-01"

# Substrings that indicate a TRANSIENT failure — order should NOT be blocked,
# the next cron tick should retry it naturally.
_TRANSIENT_HINTS = (
    '429',
    'too many requests',
    'rate limit',
    'rate-limit',
    'timeout',
    'timed out',
    'connection',
    'temporarily unavailable',
    'service unavailable',
    'bad gateway',
    'gateway timeout',
    '500',
    '502',
    '503',
    '504',
)


def _is_transient_error(message):
    if not message:
        return False
    m = str(message).lower()
    return any(hint in m for hint in _TRANSIENT_HINTS)


class _OrderAlreadyExistsError(Exception):
    pass


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopify_order_id = fields.Char(string='Shopify Order ID', copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance')
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)
    shopify_export_blocked = fields.Boolean(
        string='Shopify Export Blocked',
        default=False,
        copy=False,
        help="If True, the scheduled exporter will skip this order. "
             "Set automatically when an export attempt fails so the cron can move on. "
             "Use 'Retry Shopify Export' to clear and re-queue.",
    )
    shopify_export_error = fields.Text(
        string='Shopify Export Error',
        copy=False,
        help="Last error returned by Shopify or raised during export.",
    )
    shopify_export_attempts = fields.Integer(
        string='Shopify Export Attempts',
        default=0,
        copy=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Public action
    # ─────────────────────────────────────────────────────────────────────────

    def action_export_to_shopify(self):
        success_orders = []
        existing_orders = []
        error_messages = []

        for order in self:
            instance = order.shopify_instance_id
            try:
                order._export_to_shopify()
                order.write({
                    'shopify_export_attempts': (order.shopify_export_attempts or 0) + 1,
                    'shopify_export_error': False,
                    'shopify_export_blocked': False,
                })
                success_orders.append(order.name)
                order._write_export_log('success', instance)

            except _OrderAlreadyExistsError:
                order.write({
                    'is_exported_to_shopify': True,
                    'shopify_export_attempts': (order.shopify_export_attempts or 0) + 1,
                    'shopify_export_error': False,
                    'shopify_export_blocked': False,
                })
                existing_orders.append(order.name)
                order._write_export_log('skipped', instance)

            except Exception as e:
                error_str = str(e)
                transient = _is_transient_error(error_str)
                order.write({
                    'shopify_export_attempts': (order.shopify_export_attempts or 0) + 1,
                    'shopify_export_error': error_str,
                    'shopify_export_blocked': not transient,
                })
                error_messages.append(f"{order.name}: {e}")
                order._write_export_log('error', instance, error_message=error_str)

        message_parts = []
        if success_orders:
            message_parts.append(_("Orders exported successfully: %s") % ", ".join(success_orders[:10]))
        if existing_orders:
            message_parts.append(_("Already exists in Shopify: %s") % ", ".join(existing_orders))
        if error_messages:
            message_parts.append("\n".join(error_messages[:5]))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Sync Results'),
                'message': "\n\n".join(message_parts),
                'type': 'success' if not error_messages else 'warning',
                'sticky': bool(error_messages),
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Core export
    # ─────────────────────────────────────────────────────────────────────────

    def _export_to_shopify(self):
        self.ensure_one()

        instance = self._resolve_instance()
        session = self._make_session(instance)
        shop_url = (instance.shop_url or "").replace('https://', '').replace('http://', '').strip('/')

        # ── 1. Ensure customer exists on Shopify ──────────────────────────────
        partner = self.partner_id
        if not partner.shopify_customer_id:
            if partner.cant_export_to_shopify:
                reason = f"Customer '{partner.name}' is blocked from Shopify export (cant_export_to_shopify is set)."
                raise UserError(reason)
            if not partner.shopify_instance_id:
                partner.shopify_instance_id = instance.id
            try:
                partner._export_to_shopify(session, instance)
            except Exception as e:
                raise UserError(_("Auto-export of customer '%s' failed: %s") % (partner.name, e))

        # ── 2. Check existing order on Shopify ────────────────────────────────
        if self.shopify_order_id:
            check = session.get(
                f"https://{shop_url}/admin/api/{API}/orders/{self.shopify_order_id}.json",
                timeout=20,
            )
            if check.status_code == 200:
                pass  # Order exists — step 6 will PUT-update it
            elif check.status_code == 404:
                _logger.warning("Shopify order ID %s stale for '%s' — recreating.", self.shopify_order_id, self.name)
                self.write({'shopify_order_id': False, 'is_exported_to_shopify': False})
            else:
                raise UserError(
                    _("Failed to verify Shopify order for %s. Status %s: %s")
                    % (self.name, check.status_code, check.text[:300])
                )

        # ── 3. Build line items ───────────────────────────────────────────────
        line_items = []
        for line in self.order_line:
            if line.display_type or not line.product_id:
                continue
            variant_id = line.product_id.shopify_variant_id
            item = {
                "quantity": int(line.product_uom_qty),
                "price": str(line.price_unit),
                "title": line.name or line.product_id.display_name,
            }
            if variant_id:
                try:
                    item["variant_id"] = int(variant_id)
                except (ValueError, TypeError):
                    _logger.warning(
                        "Order %s: invalid variant ID '%s' for '%s' — using custom line.",
                        self.name, variant_id, line.product_id.display_name,
                    )
            line_items.append(item)

        if not line_items:
            raise UserError(_("No valid sale order lines to export for %s.") % self.name)

        # ── 4. Build payload ──────────────────────────────────────────────────
        if not partner.shopify_customer_id:
            raise UserError(
                _("Customer '%s' has no Shopify ID. Export the customer first.") % partner.name
            )
        try:
            shopify_customer_id_int = int(partner.shopify_customer_id)
        except (ValueError, TypeError):
            raise UserError(
                _("Customer '%s' has an invalid Shopify Customer ID: '%s'.")
                % (partner.name, partner.shopify_customer_id)
            )

        order_data = {
            "order": {
                "name": self.name,
                "email": partner.email or "",
                "customer": {"id": shopify_customer_id_int},
                "line_items": line_items,
                "billing_address": self._shopify_address(self.partner_invoice_id),
                "shipping_address": self._shopify_address(self.partner_shipping_id),
                "financial_status": "paid" if self.invoice_status == 'invoiced' else "pending",
                "fulfillment_status": None,
                "currency": self.currency_id.name,
                "total_tax": str(self.amount_tax),
                "note": html2plaintext(self.note or ''),
                "tags": "Exported from Odoo",
                "inventory_behaviour": "decrement_ignoring_policy",
            }
        }
        if self.amount_tax:
            order_data["order"]["tax_lines"] = [
                {"price": str(self.amount_tax), "title": "Tax", "rate": 0.0}
            ]

        # ── 5. Metafields ────────────────────────────────────────────────────
        metafields = self._build_order_metafields()
        if metafields:
            order_data['order']['metafields'] = metafields

        # ── 6. Send (POST create or PUT update) ──────────────────────────────
        base_url = f"https://{shop_url}/admin/api/{API}/orders"

        if self.shopify_order_id:
            # UPDATE existing order — only fields Shopify allows updating
            update_payload = {
                "order": {
                    "id":               int(self.shopify_order_id),
                    "email":            partner.email or "",
                    "note":             html2plaintext(self.note or ''),
                    "tags":             "Exported from Odoo",
                    "shipping_address": self._shopify_address(self.partner_shipping_id),
                }
            }
            resp = session.put(
                f"{base_url}/{self.shopify_order_id}.json",
                data=json.dumps(update_payload),
                timeout=20,
            )
            _logger.info("Shopify order PUT '%s' → %s", self.name, resp.status_code)

            if resp.status_code == 404:
                _logger.warning("Shopify order ID %s stale for '%s' — recreating.", self.shopify_order_id, self.name)
                self.write({'shopify_order_id': False, 'is_exported_to_shopify': False})
                resp = session.post(
                    f"{base_url}.json",
                    data=json.dumps(order_data),
                    timeout=20,
                )
                _logger.info("Shopify order POST (recovery) '%s' → %s", self.name, resp.status_code)

            if resp.status_code in (200, 201):
                data = resp.json().get('order', {})
                self.write({
                    'shopify_order_id':       str(data.get('id', '') or self.shopify_order_id),
                    'is_exported_to_shopify': True,
                })
                self._push_order_metafields(session, shop_url, self.shopify_order_id)
            else:
                raise UserError(
                    _("Shopify order update failed for %s. Status %s:\n%s")
                    % (self.name, resp.status_code, resp.text[:500])
                )
        else:
            # CREATE new order
            resp = session.post(
                f"{base_url}.json",
                data=json.dumps(order_data),
                timeout=20,
            )
            _logger.info("Shopify order POST '%s' → %s", self.name, resp.status_code)

            if resp.status_code in (200, 201):
                data = resp.json().get('order', {})
                self.write({
                    'shopify_order_id':       str(data.get('id', '')),
                    'is_exported_to_shopify': True,
                })
            else:
                raise UserError(
                    _("Shopify export failed for %s. Status %s:\n%s")
                    % (self.name, resp.status_code, resp.text[:500])
                )

    # def _get_shopify_financial_status(self):
    #     if self.pay_processed:
    #         return "paid"
    #     if self.invoice_status == 'invoiced':
    #         return "paid"
    #     return "pending"
    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_order_metafields(self):
        self.ensure_one()
        metafields = []

        # Single line text fields
        text_fields = {
            'fiscal_position_id': self.fiscal_position_id.name,
            'source_id': self.source_id.name,
            'medium_id': self.medium_id.name,
            'campaign_id': self.campaign_id.name,
            'opportunity_id': self.opportunity_id.name,
            'client_order_ref': self.client_order_ref or '',
            'picking_policy': self.picking_policy or '',
            'incoterm_location': self.incoterm_location or '',
            'incoterm': self.incoterm.id,
            'exemption_code_id': self.exemption_code_id.code or '',
            'exemption_code': self.exemption_code or '',
            'pricelist_id': self.pricelist_id.name,
            'team_id': self.team_id.name,
            'user_id': self.user_id.name,
            'partner_id': self.partner_id.ref or '',
            'sales_agent': self.sales_agent.name if self.sales_agent else '',
        }
        for key, value in text_fields.items():
            if value:
                metafields.append({
                    'namespace': 'custom',
                    'key': key,
                    'value': str(value),
                    'type': 'single_line_text_field',
                })

        # Delivery date — date_time type required by Shopify definition
        if self.commitment_date:
            metafields.append({
                'namespace': 'custom',
                'key': 'delivery_date',
                'value': self.commitment_date.isoformat(),
                'type': 'date_time',
            })

        # Odoo order ID (integer)
        metafields.append({
            'namespace': 'custom',
            'key': 'order_id',
            'value': str(self.id),
            'type': 'number_integer',
        })

        # Boolean metafields
        bool_fields = {
            'po': self.po_processed,
            'processed': self.processed,
            'payment_status': self.pay_processed,
        }
        for key, value in bool_fields.items():
            metafields.append({
                'namespace': 'custom',
                'key': key,
                'value': 'true' if value else 'false',
                'type': 'boolean',
            })

        return metafields

    def _push_order_metafields(self, session, shop_url, order_id):
        """Push order metafields via GraphQL metafieldsSet (same pattern as products)."""
        metafields = self._build_order_metafields()
        if not metafields:
            return
        owner_gid = f"gid://shopify/Order/{order_id}"
        inputs = [
            {
                "ownerId": owner_gid,
                "namespace": mf["namespace"],
                "key":       mf["key"],
                "value":     mf["value"],
                "type":      mf["type"],
            }
            for mf in metafields
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
                    _logger.warning("Shopify order metafields errors for '%s': %s", self.name, errors)
            except Exception as e:
                _logger.warning("Shopify order metafields failed for '%s': %s", self.name, e)

    def _shopify_address(self, partner):
        name = partner.name or ""
        parts = name.split(' ', 1)
        first, last = parts[0], (parts[1] if len(parts) > 1 else "")
        raw_phone = partner.phone or partner.mobile or ""
        digits = re.sub(r'[^\d]', '', raw_phone)
        if digits and raw_phone.strip().startswith('+'):
            phone = '+' + digits
        elif digits and partner.country_id and partner.country_id.phone_code:
            phone = f"+{partner.country_id.phone_code}{digits}"
        else:
            phone = digits
        return {
            "first_name": first,
            "last_name": last,
            "address1": partner.street or "",
            "address2": partner.street2 or "",
            "city": partner.city or "",
            "province": partner.state_id.name if partner.state_id else "",
            "country": partner.country_id.name if partner.country_id else "",
            "zip": partner.zip or "",
            "phone": phone,
        }

    def _resolve_instance(self):
        if self.shopify_instance_id:
            return self.shopify_instance_id
        instances = self.env['shopify.instance'].search([('state', '=', 'confirmed')])
        if len(instances) == 1:
            self.shopify_instance_id = instances[0].id
            return instances[0]
        raise UserError(_("Please select a Shopify Instance for order: %s") % self.name)

    @staticmethod
    def _make_session(instance):
        s = requests.Session()
        s.headers.update({
            "X-Shopify-Access-Token": instance.access_token,
            "Content-Type": "application/json",
        })
        return s

    def action_retry_shopify_export(self):
        """Clear the blocked flag and last error so the scheduled exporter
        will re-queue these orders on the next cron run."""
        self.write({
            'shopify_export_blocked': False,
            'shopify_export_error': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shopify Export'),
                'message': _("%d order(s) re-queued for Shopify export.") % len(self),
                'type': 'success',
                'sticky': False,
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Scheduled action entry point
    # ─────────────────────────────────────────────────────────────────────────

    @api.model
    def action_scheduled_export_to_shopify(self):
        """Called by ir.cron every N minutes.
        Finds all confirmed, non-exported orders and pushes them to Shopify.
        Results are written to the server log and CSV file.
        """
        # orders = self.search([
        #     ('state', '=', 'sale'),
        #     ('is_exported_to_shopify', '=', True),
        # ])
        # for order in orders:
        #     order.is_exported_to_shopify = False
        #     order.shopify_order_id = False

        # Shopify free tier rate-limit: ~4 order creations per minute is safe.
        # Each export uses several REST + GraphQL calls; do not raise this
        # without bumping your Shopify plan.
        orders = self.search([
            ('state', '=', 'sale'),
            ('is_exported_to_shopify', '=', False),
            ('shopify_export_blocked', '=', False),
        ], limit=4)

        if not orders:
            _logger.info("Shopify scheduled export: no orders to process.")
            return

        _logger.info("Shopify scheduled export: processing %d order(s) — %s",
                     len(orders), orders.mapped('name'))

        success, skipped, errors = [], [], []

        for order in orders:
            instance = order.shopify_instance_id

            if order.shopify_order_id:
                order.write({'is_exported_to_shopify': True})
                skipped.append(order.name)
                order._write_export_log('skipped', instance)
                continue

            try:
                order._export_to_shopify()
                order.write({
                    'shopify_export_attempts': (order.shopify_export_attempts or 0) + 1,
                    'shopify_export_error': False,
                    'shopify_export_blocked': False,
                })
                success.append(order.name)
                order._write_export_log('success', instance)

            except _OrderAlreadyExistsError:
                order.write({
                    'is_exported_to_shopify': True,
                    'shopify_export_attempts': (order.shopify_export_attempts or 0) + 1,
                    'shopify_export_error': False,
                    'shopify_export_blocked': False,
                })
                skipped.append(order.name)
                order._write_export_log('skipped', instance)

            except UserError as e:
                error_str = str(e)
                transient = _is_transient_error(error_str)
                order.write({
                    'shopify_export_attempts': (order.shopify_export_attempts or 0) + 1,
                    'shopify_export_error': error_str,
                    # Transient errors (rate limit, timeouts, 5xx) do NOT block —
                    # the next cron tick will retry the same order naturally.
                    'shopify_export_blocked': not transient,
                })
                if 'cant_export_to_shopify' in error_str:
                    skipped.append(order.name)
                    order._write_export_log('skipped', instance, error_message=error_str)
                    _logger.warning(
                        "Shopify scheduled export: blocking order '%s' — customer '%s' is blocked.",
                        order.name, order.partner_id.name,
                    )
                elif transient:
                    errors.append(order.name)
                    order._write_export_log('error', instance, error_message=error_str)
                    _logger.warning(
                        "Shopify scheduled export: TRANSIENT failure on '%s' — will retry next tick: %s",
                        order.name, error_str,
                    )
                    # Stop processing the rest of this batch — the bucket is
                    # almost certainly exhausted, no point hammering Shopify.
                    break
                else:
                    errors.append(order.name)
                    order._write_export_log('error', instance, error_message=error_str)
                    _logger.error(
                        "Shopify scheduled export: failed to export '%s': %s",
                        order.name, e, exc_info=True,
                    )

            except Exception as e:
                error_str = str(e)
                transient = _is_transient_error(error_str)
                order.write({
                    'shopify_export_attempts': (order.shopify_export_attempts or 0) + 1,
                    'shopify_export_error': error_str,
                    'shopify_export_blocked': not transient,
                })
                errors.append(order.name)
                order._write_export_log('error', instance, error_message=error_str)
                if transient:
                    _logger.warning(
                        "Shopify scheduled export: TRANSIENT failure on '%s' — will retry next tick: %s",
                        order.name, error_str,
                    )
                    break
                else:
                    _logger.error(
                        "Shopify scheduled export: failed to export '%s': %s",
                        order.name, e, exc_info=True,
                    )

    def _write_export_log(self, status, instance, error_message=None):
        try:
            # ── Step 1: Check data_dir ────────────────────────────────────────
            data_dir = config.get('data_dir', '/tmp')
            _logger.info("SHOPIFY LOG DEBUG — data_dir = '%s'", data_dir)

            # ── Step 2: Check/create log dir ──────────────────────────────────
            log_dir = os.path.join(data_dir, 'shopify_logs')
            _logger.info("SHOPIFY LOG DEBUG — log_dir = '%s'", log_dir)

            os.makedirs(log_dir, exist_ok=True)
            _logger.info("SHOPIFY LOG DEBUG — log_dir created/exists: %s", os.path.isdir(log_dir))

            # ── Step 3: Check write permission ────────────────────────────────
            if not os.access(log_dir, os.W_OK):
                _logger.error("SHOPIFY LOG DEBUG — NO WRITE PERMISSION on '%s'", log_dir)
                return
            _logger.info("SHOPIFY LOG DEBUG — write permission OK")

            # ── Step 4: Define log file ───────────────────────────────────────
            log_file = os.path.join(log_dir, "order_export.csv")
            file_exists = os.path.isfile(log_file)
            _logger.info("SHOPIFY LOG DEBUG — log_file = '%s', exists = %s", log_file, file_exists)

            # ── Step 5: Detect block reason ───────────────────────────────────
            block_reason = ''
            if error_message and 'cant_export_to_shopify' in error_message:
                block_reason = f"Customer '{self.partner_id.name}' is flagged as cant_export_to_shopify in Odoo."

            # ── Step 6: Write row ─────────────────────────────────────────────
            with open(log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        'Export Date', 'Order Name', 'Odoo ID',
                        'Shopify Order ID', 'Customer', 'Amount Total',
                        'Currency', 'Instance', 'Status', 'Error Message', 'Block Reason',
                    ])
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    self.name,
                    self.id,
                    self.shopify_order_id or '',
                    self.partner_id.name or '',
                    self.amount_total,
                    self.currency_id.name or '',
                    instance.name if instance else '',
                    status,
                    error_message or '',
                    block_reason,
                ])
            _logger.info("SHOPIFY LOG DEBUG — row written successfully for order '%s'", self.name)

        except Exception as e:
            _logger.error("SHOPIFY LOG DEBUG — EXCEPTION: %s | type: %s", e, type(e).__name__, exc_info=True)
