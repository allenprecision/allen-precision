import logging
from odoo import http
from odoo.http import request

try:
    from odoo.addons.portal_rating.controllers.portal_chatter import PortalChatter
except ImportError:
    from odoo.addons.portal.controllers.mail import PortalChatter

_logger = logging.getLogger(__name__)

class PortalChatterInherit(PortalChatter):

    @http.route('/mail/chatter_init', type='json', auth='public', website=True)
    def portal_chatter_init(self, res_model, res_id, domain=False, limit=False, **kwargs):
        _logger.info("APE_FIXES: portal_chatter_init called for model %s, id %s", res_model, res_id)
        result = super().portal_chatter_init(res_model, res_id, domain=domain, limit=limit, **kwargs)

        user = request.env.user
        is_portal = user.has_group('base.group_portal')
        _logger.info("APE_FIXES: User: %s, Is Portal: %s", user.name, is_portal)

        if is_portal:
            partner = user.partner_id
            search_domain = [
                ('partner_id', '=', partner.id),
                ('state', '=', 'sale'),
            ]
            has_confirmed_order = bool(request.env['sale.order'].sudo().search_count(search_domain, limit=1))

            if not has_confirmed_order:
                _logger.info("APE_FIXES: Restricting composer for user %s", user.name)
                result['options']['display_composer'] = False
                result['options']['restrict_chatter_composer'] = True

        return result
