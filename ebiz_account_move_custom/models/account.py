# -*- coding: utf-8 -*-

# imports of python lib
import json

#  imports of odoo
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_check_number = fields.Char(string="Check Number", compute='_compute_payment_check_number', store=True)

    @api.depends('invoice_payments_widget', 'payment_state', 'state')
    def _compute_payment_check_number(self):
        """
        Compute the payment check number for the accounting move record.

        The payment check number is extracted from the payment data of the accounting move record, if it exists and if the
        payment method is 'Checks'. The extracted check number is assigned to the `payment_check_number` field of the
        accounting move record.

        :return: None
        """
        # Iterate over each accounting move record
        for move in self:
            check_number = False

            # Check if the accounting move record is posted and has payment data for a check payment
            if move.state == 'posted' and move.payment_state in ('in_payment', 'paid') and move.invoice_payments_widget:
                data = move.invoice_payments_widget

                # Extract payment data from the invoice payments widget
                if data and data.get('content', False):
                    content = data['content'][0]

                    # Check if the payment method is 'Checks' and if the payment has a check number
                    if content.get('account_payment_id', False) and content.get('payment_method_name', False) == 'Checks':
                        payment_id = self.env['account.payment'].browse(data['content'][0]['account_payment_id'])
                        if payment_id and payment_id.check_number:
                            check_number = payment_id.check_number

            # Assign the check number (if any) to the `payment_check_number` field of the accounting move record
            move.payment_check_number = check_number


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # Due to the delegation inheritance, this field is being added to payments, causing confusion due to duplication.
    # That's why we're making it unsearchable for users.
    payment_check_number = fields.Char(searchable=False)