from odoo import http
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.delivery import WebsiteSaleDelivery


class AvataxWebsiteSale(WebsiteSale):
    @http.route(
        "/shop/payment", type="http", auth="public", website=True, sitemap=False
    )
    def shop_payment(self, **post):
        order = request.website.sale_get_order()
        order._avatax_compute_tax()
        return super().shop_payment(**post)

class WebsiteSaleWithAvalara(WebsiteSale):

    @http.route(['/shop/payment/validate'], type='http', auth="public", website=True, csrf=False)
    def shop_payment_validate(self, sale_order_id=None, **post):
        # Call the original method (this handles confirmation, payments, etc.)
        response = super().shop_payment_validate(sale_order_id=sale_order_id, **post)

        # After the original logic, fetch the confirmed order
        order = request.env['sale.order'].sudo().browse(
            request.session.get('sale_last_order_id')
        ).exists()

        # If Avalara is enabled, compute taxes
        if order and order.state == 'sale':
            order.avalara_compute_taxes()

        return response

class WebsiteSaleDeliveryEbiz(WebsiteSaleDelivery):

    @http.route()
    def update_eshop_carrier(self, **post):
        order = request.website.sale_get_order()
        order._avatax_compute_tax()
        res=super(WebsiteSaleDeliveryEbiz, self).update_eshop_carrier(**post)
        return res

    def _update_website_sale_delivery_return(self, order, **post):
        Monetary = request.env['ir.qweb.field.monetary']
        carrier_id = int(post['carrier_id'])
        currency = order.currency_id
        if order:
            #avatax fixed issued
            order._avatax_compute_tax()
            return {
                'status': order.delivery_rating_success,
                'error_message': order.delivery_message,
                'carrier_id': carrier_id,
                'is_free_delivery': not bool(order.amount_delivery),
                'new_amount_delivery': Monetary.value_to_html(order.amount_delivery, {'display_currency': currency}),
                'new_amount_untaxed': Monetary.value_to_html(order.amount_untaxed, {'display_currency': currency}),
                'new_amount_tax': Monetary.value_to_html(order.amount_tax, {'display_currency': currency}),
                'new_amount_total': Monetary.value_to_html(order.amount_total, {'display_currency': currency}),
                'new_amount_total_raw': order.amount_total,
            }
        return {}
