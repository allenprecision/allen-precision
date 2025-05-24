# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('line_ids.account_id.account_type',
                 'line_ids.account_id',
                 'line_ids')
    def _get_cost_cogs(self):
        """
        Computes the Cost of Goods Sold (COGS) for each customer invoice and credit note.

        It computes the sum of the debit/credit amount for the move lines that belong to
        accounts with account_type = 'expense_direct_cost'.
        """
        move_type_mappings = {'out_invoice': 'debit', 'out_refund': 'credit'}
        cogs_account_type = 'expense_direct_cost'

        for move in self:
            move_type = move.move_type
            if move_type in move_type_mappings.keys():
                cost_cogs = sum(
                    move.line_ids.filtered_domain(
                        [('account_id.account_type', '=', cogs_account_type)]
                    ).mapped(move_type_mappings[move_type])
                ) or 0

                if move_type == 'out_refund':
                    cost_cogs = -abs(cost_cogs)

                move.cost_cogs = cost_cogs
            else:
                move.cost_cogs = 0

    def _get_cost(self):
        """
        Computes the total cost of each move.
        """
        for move in self:
            income_accounts = self.env['account.account'].search(
                [('internal_group', '=', 'income'), ('deprecated', '=', False)]
            )
            move.cost_move_lines = sum(
                move.line_ids.filtered_domain([('account_id', 'in', income_accounts.ids)]).mapped('cost')
            ) or 0

    def _get_cost_runtime(self):
        """
        Computes the runtime cost for each move.
        """
        for move in self:
            move.cost_runtime = sum(
                x.product_id.standard_price * x.quantity for x in move.invoice_line_ids
            ) or 0

    customer_number = fields.Char(
        string="Customer Number", store=True, compute="_get_customer_number"
    )
    cost_runtime = fields.Float(
        compute='_get_cost_runtime', string='Cost Runtime'
    )
    cost_cogs = fields.Float(
        compute='_get_cost_cogs', string="COGS", store=True
    )
    cost_move_lines = fields.Float(
        compute='_get_cost', string='Cost'
    )

    @api.depends('partner_id')
    def _get_customer_number(self):
        for rec in self:
            if rec.partner_id:
                rec.customer_number = rec.partner_id.parent_id.ref or rec.partner_id.ref
            else:
                rec.customer_number = False

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res["invoice_date"] = datetime.now().date()
        return res

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('product_id', 'quantity')
    def _calc_cost(self):
        for rec in self:
            rec.cost = 0.0 if rec.product_id.rent_ok else rec.product_id.standard_price * rec.quantity

    @api.depends('account_id.account_type',
                 'product_id',
                 'move_id',
                 'move_id.move_type',
                 'move_id.line_ids',
                 'move_id.cost_cogs')
    def _get_cost_cogs(self):
        """
        Computes the Cost of Goods Sold (COGS) for each customer invoice and credit note.
        """
        move_type_mappings = {'out_invoice': 'debit', 'out_refund': 'credit'}
        cogs_account_type = 'expense_direct_cost'

        for line in self:
            line.cost_cogs = 0

            # Handle lines with the same product to avoid double-counting
            same_product_lines = line.move_id.invoice_line_ids.filtered_domain(
                [('product_id', '=', line.product_id.id)]
            )
            if len(same_product_lines) > 1 and same_product_lines.filtered_domain([('cost_cogs', '!=', 0)]):
                continue

            move = line.move_id
            move_type = move.move_type

            if move_type in move_type_mappings.keys():
                cost_cogs = sum(
                    move.line_ids.filtered_domain(
                        [('account_id.account_type', '=', cogs_account_type), ('product_id', '=', line.product_id.id)]
                    ).mapped(move_type_mappings[move_type])
                ) or 0

                if move_type == 'out_refund':
                    cost_cogs = -abs(cost_cogs)

                line.cost_cogs = cost_cogs

    cost_cogs = fields.Float(
        compute='_get_cost_cogs', string="COGS", store=True
    )
    cost = fields.Float(
        string='Cost Price', compute='_calc_cost', store=True
    )


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    cost_cogs = fields.Float(string="COGS", readonly=True)

    _depends = {
        'account.move.line': ['cost_cogs'],
    }

    def _select(self):
        return super()._select() + ", line.cost_cogs as cost_cogs"

