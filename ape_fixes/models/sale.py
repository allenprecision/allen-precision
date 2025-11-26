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


