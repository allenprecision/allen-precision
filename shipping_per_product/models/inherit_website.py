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


class inheritResConfig(models.TransientModel):
    _inherit = "res.config.settings"

    wk_enable_product_shipping = fields.Boolean("Shipping Per Product",related="website_id.enable_product_shipping",help="Deliveries will be managed and available on the basis of products for the selected website.",readonly=False)

class inheritWebsite(models.Model):
    _inherit = "website"


    enable_product_shipping = fields.Boolean("Shipping Per Product",help="Deliveries will be managed and available on the basis of products for this website.")
    is_grouping_items = fields.Boolean("Enable Items Grouping", help=" if enabled, on checkout page item will be grouped when same set of delivery method are selected in backend.")
