import werkzeug
from odoo import http, api
from odoo.http import request
import base64


class GoogleFeedFileUrl(http.Controller):
    @http.route('/google_feed_file_url/<string:id>', type='http', auth='public', website=True, sitemap=False,
                csrf=False)
    def google_feed_file_url(self, **args):
        feed_ids = request.env['google.feed.config'].sudo().search([('feed_number', '=', args['id'])])
        file_data = base64.decodebytes(feed_ids.feed_file)
        if feed_ids.file_type == 'xml':
            return werkzeug.wrappers.Response(
                status=200,
                content_type="application/xml; charset=utf-8",
                response=file_data
            )
        if feed_ids.file_type == 'txt':
            file_data = str(file_data, 'utf-8')
            return werkzeug.wrappers.Response(
                status=200,
                response=file_data
            )
