# -*- coding: utf-8 -*-

from odoo import models, fields

class PriceListExtend(models.Model):
    _inherit = 'product.pricelist.item'
    _description = 'Product Discount Countdown'

    show_timer = fields.Boolean(string='Display Timer', default=True)
