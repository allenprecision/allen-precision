# controllers/main.py
from odoo import http
from odoo.http import request

class WebsiteMaintenance(http.Controller):

    @http.route(['/maintenance'], type='http', auth="public", website=True)
    def maintenance(self, **kwargs):
        return 'Hello!'

    @http.route(website=True, auth="public", type='http')
    def catch_all(self, **kwargs):
        """ Catch-all route for maintenance """
        user = request.env.user
        if not user.has_group('base.group_user'):  # if not an internal user
            return request.redirect('/maintenance')
        # fallback: let internal users access the original page
        return request._serve_static_or_redirect()

# hooks.py or part of your controller
from odoo.http import request, route, Controller
from odoo import http

class MaintenanceMiddleware(http.Controller):

    @http.before_request
    def block_public_users(self):
        # Skip XML-RPC, JSON-RPC, backend routes, static assets
        if request.endpoint and request.endpoint.routing.get('auth') != 'public':
            return

        # Allow internal users (i.e., backend users)
        if request.env.user.has_group('base.group_user'):
            return

        # Allow access to the maintenance route itself
        if request.httprequest.path == '/maintenance':
            return

        # Redirect all other public routes to maintenance page
        return request.redirect('/maintenance')

