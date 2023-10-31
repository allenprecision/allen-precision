# -*- coding: utf-8 -*-
##########################################################################
# 2010-2017 Webkul.
#
# NOTICE OF LICENSE
#
# All right is reserved,
# Please go through this link for complete license : https://store.webkul.com/license.html
#
# DISCLAIMER
#
# Do not edit or add to this file if you wish to upgrade this module to newer
# versions in the future. If you wish to customize this module for your
# needs please refer to https://store.webkul.com/customisation-guidelines/ for more information.
#
# @Author        : Webkul Software Pvt. Ltd. (<support@webkul.com>)
# @Copyright (c) : 2010-2017 Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# @License       : https://store.webkul.com/license.html
#
##########################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'


    def get_line_ids(self):
        order_id = self.env['sale.order'].browse(self._context.get('active_id'))
        line_ids = order_id.order_line.filtered(lambda l: l.product_id.type != 'service' and l.is_delivery == False)
        return line_ids


    line_ids = fields.Many2many("sale.order.line",default=get_line_ids)
    is_sol_carrier = fields.Boolean("SOL Carrier", related="carrier_id.is_sol_carrier")

    @api.onchange('carrier_id')
    def _onchange_carrier_id(self):
        if self.is_sol_carrier:
            self.delivery_message = False
            self.display_price = 0
            self.delivery_price = 0
        else:
            return super(ChooseDeliveryCarrier, self)._onchange_carrier_id()

    def _get_shipment_rate(self):
        if self.is_sol_carrier:
            without_delivery_lines = self.line_ids.filtered(lambda l : not l.delivery_carrier_id)
            if without_delivery_lines:
                message =",".join([line.product_id.name for line in without_delivery_lines])
                raise UserError("Please first select the delivery method for ({}) products.".format(message))
            else:
                vals = self.carrier_id.sol_carrier_rate_shipment(self.order_id)
                if vals.get('success'):
                    self.delivery_message = vals.get('warning_message', False)
                    self.delivery_price = vals['price']
                    self.display_price = vals['carrier_price']
                    return {}
                elif vals.get('error_message',False):
                    return {'error_message': vals['error_message']}
                else:
                    return{'error_message' :'Something went wrong .'}
        else:
            return super(ChooseDeliveryCarrier, self)._get_shipment_rate()
