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
from odoo import http, _
from odoo.tools import float_round
from odoo.http import request
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery as WSaleDelivery

import logging
_logger = logging.getLogger(__name__)

class ProductShipping(http.Controller):

    def sol_update_website_sale_delivery_return(self, order, carrier_id, lines):
        FieldMonetary = request.env['ir.qweb.field.monetary']
        monetary_options = {
            'display_currency': request.website.get_current_pricelist().currency_id,
        }
        if order:
            sol_delivery_amount = sum(lines.mapped('delivery_charge'))
            new_total_delivery_amount = order.get_total_sol_delivery_price()
            values = {
                'status': order.delivery_rating_success,
                'error_message': order.delivery_message,
                'carrier_id': carrier_id,
                'is_free_delivery': not bool(order.amount_delivery),
                'sol_delivery_amount': FieldMonetary.value_to_html(sol_delivery_amount,monetary_options),
                'new_amount_delivery': FieldMonetary.value_to_html(new_total_delivery_amount,monetary_options),
                'new_amount_untaxed': FieldMonetary.value_to_html(order.amount_untaxed,monetary_options),
                'new_amount_tax': FieldMonetary.value_to_html(order.amount_tax,monetary_options),
                'new_amount_total': FieldMonetary.value_to_html(order.amount_total,monetary_options),
                'new_amount_total_raw': order.amount_total,
            }
            return values
        return {}

    @http.route(['/shop/sol/update_carrier'], type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def update_shop_sol_carrier(self, **post):
        order = request.website.sale_get_order()
        carrier_id = int(post['carrier_id'])
        order_lines = post.get('order_lines')
        order_lines = request.env["sale.order.line"].sudo().browse(order_lines)
        if order:
            order._check_carrier_sol_quotation(force_carrier_id=carrier_id, lines=order_lines)
        return self.sol_update_website_sale_delivery_return(order, carrier_id, order_lines)


class WebsiteSaleDelivery(WSaleDelivery):
    def _get_shop_payment_values(self, order, **kwargs):
        if request.website and not request.website.enable_product_shipping:
            return super(WebsiteSaleDelivery, self)._get_shop_payment_values(order, **kwargs)

        values = super(WSaleDelivery, self)._get_shop_payment_values(order, **kwargs)
        has_storable_products = any(line.product_id.type in ['consu', 'product'] for line in order.order_line)
        
        if has_storable_products:
            if order.carrier_id and not order.delivery_rating_success:
                order._remove_delivery_line()

            delivery_carriers = order._wk_get_delivery_methods()
            values['deliveries'] = delivery_carriers.sudo()

        values['delivery_has_storable'] = has_storable_products
        values['delivery_action_id'] = request.env.ref('delivery.action_delivery_carrier_form').id
        return values
        
