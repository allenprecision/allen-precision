from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        Blocklist = self.env['email.domain.blocklist'].sudo()
        for vals in vals_list:
            if vals.get('email'):
                Blocklist.check_email_allowed(vals['email'])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('email'):
            self.env['email.domain.blocklist'].sudo().check_email_allowed(vals['email'])
        return super().write(vals)
