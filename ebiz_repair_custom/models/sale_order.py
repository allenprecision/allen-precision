# -*- coding: utf-8 -*-

from odoo import fields, models


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    product_information = fields.Char()