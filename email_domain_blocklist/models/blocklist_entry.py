import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BlocklistEntry(models.Model):
    _name = 'email.domain.blocklist'
    _description = 'Email / Domain Blocklist Entry'
    _order = 'value'

    name = fields.Char(string='Description')
    value = fields.Char(
        string='Blocked String',
        required=True,
        help="Any string. An email is blocked if it contains this string "
             "(case insensitive). E.g. 'gmail.com' blocks every gmail address; "
             "'xyz@gmail.com' blocks 1xyz@gmail.com, 2xyz@gmail.com, etc.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('value_uniq', 'unique(value)',
         'This string is already in the blocklist.'),
    ]

    @api.constrains('value')
    def _check_value(self):
        for rec in self:
            if not (rec.value or '').strip():
                raise ValidationError(_("Value cannot be empty."))

    @api.model
    def create(self, vals):
        # Only strip whitespace. Matching is case-insensitive at query time.
        if vals.get('value'):
            vals['value'] = vals['value'].strip()
        return super().create(vals)

    def write(self, vals):
        if vals.get('value'):
            vals['value'] = vals['value'].strip()
        return super().write(vals)

    # ------------------------------------------------------------------
    # Matching helpers
    # ------------------------------------------------------------------
    @api.model
    def _normalize_email(self, email):
        if not email:
            return ''
        # take the address part if a "Name <addr>" form is given
        match = re.search(r'<([^>]+)>', email)
        if match:
            email = match.group(1)
        return re.sub(r'\s+', '', email).lower()

    @api.model
    def is_blocked(self, email):
        """Return the matching blocklist record (or empty recordset).
        An email is blocked if it CONTAINS any blocklist value as a substring.
        Matching is case-insensitive."""
        email = self._normalize_email(email)
        if not email:
            return self.browse()
        for entry in self.search([]):
            if entry.value and entry.value.lower() in email:
                return entry
        return self.browse()

    @api.model
    def check_email_allowed(self, email):
        """Raise ValidationError if the email is blocked."""
        if self.is_blocked(email):
            raise ValidationError(
                _("Registration with the email '%s' is not allowed.") % email
            )
        return True
