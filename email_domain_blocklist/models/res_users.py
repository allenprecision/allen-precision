from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _validate_blocklist(self, vals):
        Blocklist = self.env['email.domain.blocklist'].sudo()
        for key in ('login', 'email'):
            if vals.get(key):
                Blocklist.check_email_allowed(vals[key])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._validate_blocklist(vals)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('login') or vals.get('email'):
            self._validate_blocklist(vals)
        return super().write(vals)

    @api.model
    def signup(self, values, token=None):
        # Portal / website self-signup path.
        email = values.get('email') or values.get('login')
        if email:
            self.env['email.domain.blocklist'].sudo().check_email_allowed(email)
        return super().signup(values, token=token)
