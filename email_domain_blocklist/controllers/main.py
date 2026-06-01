from odoo import http, _
from odoo.http import request

# Will raise ImportError on backend-only installs -> handled in __init__.
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleBlocklist(WebsiteSale):

    def _is_email_blocked(self, email):
        return bool(
            request.env['email.domain.blocklist'].sudo().is_blocked(email)
        )

    def checkout_form_validate(self, mode, all_form_values, data):
        errors, error_msg = super().checkout_form_validate(
            mode, all_form_values, data
        )
        email = data.get('email')
        if email and self._is_email_blocked(email):
            errors['email'] = 'error'
            error_msg.append(
                _("Orders from the email '%s' are not allowed.") % email
            )
        return errors, error_msg

    @http.route()
    def shop_payment(self, **post):
        # Final guard before payment: re-check the order partner's email.
        order = request.website.sale_get_order()
        if order and order.partner_id.email and \
                self._is_email_blocked(order.partner_id.email):
            return request.redirect('/shop/checkout?blocked=1')
        return super().shop_payment(**post)
