from odoo import fields, models


class GoogleOptionalFields(models.Model):
    _name = 'google.optional.fields'
    _description = 'This model is used to add the optional fields for google Feed'

    google_tag_name = fields.Char('Google Tag Name')
    product_field = fields.Many2one('ir.model.fields', string='Product Field')
    variant_field = fields.Many2one('ir.model.fields', string='Variant Field')
    feed_id = fields.Many2one('google.feed.config', string="Feed")
    product_type = fields.Selection(related="feed_id.product_type")

