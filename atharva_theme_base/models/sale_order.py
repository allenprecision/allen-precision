# -*- coding: utf-8 -*-

from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_shipping_details(self):
        domain = [('website_published', '=', True), ('delivery_type', '=', 'fixed')]
        carriers = self.env['delivery.carrier'].sudo().search(domain).available_carriers(self.partner_shipping_id)
        total_amount = self._compute_amount_total_without_delivery()
        carries_amount = 0
        status = 0
        any_ns_product = False
        min_fix_price = min(carriers, key=lambda x: x.fixed_price) if carriers else 0
        any_ns_product = any(line.product_id.type != 'service' for line in self.order_line)
        if min_fix_price and min_fix_price.fixed_price <= 0:
            return {
                'carries_amount': carries_amount,
                'total_amount': total_amount,
                'pending_amount': carries_amount - total_amount,
                'status': 100,
                'amount': min_fix_price.fixed_price if min_fix_price else 0,
                'any_ns_product': any_ns_product
            }
        else:
            domain = [('website_published', '=', True), ('delivery_type', '=', 'fixed'), ('free_over', '=', True)]
            carriers = self.env['delivery.carrier'].sudo().search(domain).available_carriers(self.partner_shipping_id)
            min_carrier = min(carriers, key=lambda x: x.amount) if carriers else 0
            if min_carrier and min_carrier.amount > 0:
                status = (total_amount * 100) / min_carrier.amount
            return {
                'carries_amount': min_carrier.amount if min_carrier else 0,
                'total_amount': total_amount,
                'pending_amount': min_carrier.amount - total_amount if min_carrier else 0,
                'status': status,
                'amount': 0,
                'any_ns_product':any_ns_product
            }