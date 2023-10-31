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

import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    delivery_carrier_ids = fields.Many2many("delivery.carrier", "product_delivery_carriers", "product_temp_ids", "delivery_carrier_ids", string="Delivery Methods")

    @api.onchange('type')
    def set_delivery_carriers_for_service(self):
        if self.type == 'service':
            self.delivery_carrier_ids = False
