# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# License URL : https://store.webkul.com/license.html/
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_carrier_quotation(self, force_carrier_id=None):
        if self.website_id and self.website_id.enable_product_shipping:
            self._remove_delivery_line()
            self.write({'carrier_id': False})
            self.order_line.filtered('is_delivered').write({
                'delivery_carrier_id' : False,
                'delivery_charge' : 0.0,
                'is_delivered': False
            })
            return True
        return super(SaleOrder, self)._check_carrier_quotation(force_carrier_id=force_carrier_id)



    def _check_carrier_sol_quotation(self, force_carrier_id=None, lines=None):
        self.ensure_one()
        DeliveryCarrier = self.env['delivery.carrier']
        if self.only_services:
            self.write({'carrier_id': None})
            self._remove_delivery_line()
            return True
        else:
            # attempt to use partner's preferred carrier
            if not force_carrier_id and self.partner_shipping_id.property_delivery_carrier_id:
                force_carrier_id = self.partner_shipping_id.property_delivery_carrier_id.id
            carrier = force_carrier_id and DeliveryCarrier.browse(force_carrier_id) or self.carrier_id
            if carrier:
                sol_carrier = DeliveryCarrier.search([('is_sol_carrier','=',True)],limit=1)
                sol_free_config = True if sol_carrier and sol_carrier.sol_free_config == 'y' else None

                res = carrier.sol_carrier_rate_shipment(self, lines=lines, sol_free_config=sol_free_config)

                if sol_carrier:
                    carrier = sol_carrier
                if res.get('success'):
                    shipping_cost = self.get_total_sol_delivery_price()
                    self.set_delivery_line(carrier, shipping_cost)
                    self.delivery_rating_success = True
                    self.delivery_message = res['warning_message']
                else:
                    self.set_delivery_line(carrier, 0.0)
                    self.delivery_rating_success = False
                    self.delivery_message = res['error_message']
        return bool(carrier)

    def get_total_sol_delivery_price(self):
        amount = sum(self.order_line.filtered('is_delivered').mapped('delivery_charge'))
        return amount

    def get_lines_with_or_without_delivery(self):
        """This method used on payment page. Return [{lines, deliveries}]]"""
        self.ensure_one()
        order_lines = self.website_order_line
        service_lines = order_lines.filtered(lambda l: l.product_id.type == 'service')
        non_service_lines = order_lines - service_lines
        data = {}
        for line in non_service_lines:
            deliveries = line.get_delivery_carrier_ids()
            if deliveries:
                del_key = "/".join(map(str, deliveries.ids))
                if data.get(del_key):
                    data[del_key]['lines'] += line
                else:
                    data[del_key] = {'lines': line, 'deliveries': deliveries, 'type': 'non_service'}
            else:
                if data.get('without'):
                    data['without']['lines'] += line
                else:
                    data['without'] = {'lines': line, 'deliveries': None, 'type': 'non_service'}
        if data.get('without'):
            deliveries = self._get_delivery_methods()
            del_key = "/".join(map(str, deliveries.ids))
            if data.get(del_key,False):
                data[del_key]["lines"] += data["without"]['lines']
                del data['without']
            else:
                data['without']['deliveries'] = deliveries
        if service_lines:
            data['service'] = {'lines': service_lines, 'deliveries': None, 'type': 'service'}
        return list(data.values())

    def _get_delivery_methods(self):
        methods = super(SaleOrder, self)._get_delivery_methods()
        if self.website_id and self.website_id.enable_product_shipping:
            return methods.filtered(lambda m: not m.product_specific)
        return methods

    def _wk_get_delivery_methods(self):
        """ 
        If there is no delivery associated in any product (except service type) in the cart 
        line this method return blank delivery.carrier() otherwise 
        it returns all available delivery line objectes delivery.carrier(1,2,3)

        If delivery not available pay now button will not be visible
        """
        deliveries = self.get_lines_with_or_without_delivery()
        delivery_objs = self.env['delivery.carrier']
        for delivery_dict in deliveries:
            if delivery_dict.get('type') == 'service':
                continue
            if not delivery_dict.get('deliveries'):
                return self.env['delivery.carrier']
            delivery_objs |= delivery_dict['deliveries']
        return delivery_objs

class SaleOderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends("product_id")
    def _compute_available_carrier(self):
        for rec in self:
            carriers = rec.get_delivery_carrier_ids()
            if carriers:
                rec.available_carrier_ids = carriers
            else:
                carriers = self.env['delivery.carrier'].sudo().search([('website_published','=',True),('is_sol_carrier','=',False),('product_specific','=',False)])
                rec.available_carrier_ids = carriers.available_carriers(rec.order_id.partner_shipping_id)

    delivery_carrier_id = fields.Many2one("delivery.carrier", string="Delivery Method")
    delivery_charge = fields.Float("Delivery Price", readonly=True, copy=False)
    available_carrier_ids = fields.Many2many("delivery.carrier", compute='_compute_available_carrier', string="Available Carriers")
    is_delivered = fields.Boolean("Delivered")
    unique_grp_key = fields.Char("Delivery Grouping Key")
    active = fields.Boolean("Active", default=True)

    @api.onchange('product_id')
    def set_deliver_carrier_for_product(self):
        if self.product_id.type == 'service':
            self.delivery_carrier_id = False

    def get_delivery_carrier_ids(self):
        self.ensure_one()
        address = self.order_id.partner_shipping_id
        delivery_carriers = self.product_id.product_tmpl_id.delivery_carrier_ids.filtered('website_published')
        data = delivery_carriers.available_carriers(address)
        return data
