# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
from datetime import datetime
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    customer_number = fields.Char(related="partner_id.ref", string="Customer Number")
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="[('contact_type','!=','ven'),'|', ('company_id', '=', False), ('company_id', '=', company_id)]", )

    delivery_address = fields.Html(string='Delivery Address ', compute='_delivery_address', store=True)
    sales_agent = fields.Many2one('res.users', string='Sales Agent')
    processed = fields.Boolean('Processed', default=False)
    processed_value = fields.Selection([('', ''), ('processed', 'Processed')], 'Processed',
                                       compute="get_process_value")


    po_processed = fields.Boolean('PO', default=False)
    po_processed_value = fields.Selection([('', ''), ('po_processed', 'PO ')], 'PO',
                                       compute="get_po_process_value")

    pay_processed = fields.Boolean('Payment Status', default=False)
    pay_processed_value = fields.Selection([('not_paid', 'Unpaid'), ('paid', 'Paid')], 'Payment Status',
                                       compute="get_pay_process_value")

    def write(self, vals):
        """
        Override write to check updated values in vals
        """
        limit_date = datetime(2025, 11, 12, 0, 0, 0)
        # Example 1: Check if a specific field is being updated
        if 'state' in vals:
            _logger.info(f'State: {vals}, payment terms: {self.payment_term_id}, create date: {self.create_date}')
            if vals['state'] == 'sale' and self.payment_term_id.name == 'CHARGE CARD' and self.create_date > limit_date:
                _logger.info('Condition matched')
                vals['pay_processed'] = True
        # elif 'payment_terms' in vals:
        #     if self.state == 'sale' and vals['payment_term_id'] == 'CHARGE CARD' and self.date_order > limit_date:
        #         vals['pay_processed'] = True
        # Always call super
        return super(SaleOrder, self).write(vals)

    def get_pay_process_value(self):
        for rec in self:
            if rec.pay_processed:
                rec.pay_processed_value = 'paid'
            else:
                rec.pay_processed_value = 'not_paid'

    def get_po_process_value(self):
        for rec in self:
            if rec.po_processed:
                rec.po_processed_value = 'po_processed'
            else:
                rec.po_processed_value = ''

    def get_process_value(self):
        for rec in self:
            if rec.processed:
                rec.processed_value = 'processed'
            else:
                rec.processed_value = ''

    @api.depends('partner_shipping_id')
    def _delivery_address(self):
        for rec in self:
            if rec.partner_shipping_id:
                if rec.partner_shipping_id.street2:
                    rec.delivery_address = f"<pre>{rec.partner_shipping_id.street}<br>{rec.partner_shipping_id.street2}<br>{rec.partner_shipping_id.city} {rec.partner_shipping_id.state_id.code} {rec.partner_shipping_id.zip}<br>{rec.partner_shipping_id.country_id.name}</pre>"
                else:
                    rec.delivery_address = f"<pre>{rec.partner_shipping_id.street}<br>{rec.partner_shipping_id.city} {rec.partner_shipping_id.state_id.code} {rec.partner_shipping_id.zip}<br>{rec.partner_shipping_id.country_id.name}</pre>"
            else:
                rec.delivery_address = False

# @api.model
# def create(self,vals):
#     if vals.get('partner_id'):
#         partner = self.env['res.partner'].sudo().browse(int(vals.get('partner_id')))
#         if not partner.ref:
#             raise UserError('Cannot create sale order for customer not having customer number')
#     res = super(SaleOrder,self).create(vals)
#     return res


