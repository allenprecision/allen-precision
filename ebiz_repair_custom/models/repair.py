# -*- coding: utf-8 -*-

from odoo import fields, models


class Repair(models.Model):
    _inherit = 'repair.order'

    product_information = fields.Char()

    def action_create_sale_order(self):
        # Call the original method to perform its functionality
        result = super().action_create_sale_order()

        # Assign the product_information field value to the created sale orders
        for repair in self:
            if repair.sale_order_id:
                repair.sale_order_id.product_information = repair.product_information

        return result
