from odoo import api, fields, models, _


class FeedProcessErrorLog(models.Model):
    _name = 'feed.process.error.log'
    _description = 'Feed Process error log file'
    _order = 'error_datetime desc'
    _rec_name = 'feed_id'

    feed_id = fields.Many2one('google.feed.config', string='Feed')
    error_datetime = fields.Datetime('DateTime')
    product_id = fields.Many2one('product.template', string='Product')
    variant_id = fields.Many2one('product.product', string='Product')
    error_message = fields.Char('Error')
    file_name = fields.Char('File')
    name = fields.Char('Name', related='product_id.name')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    error_history_id = fields.Many2one('feed.process.error.log', string="Error History")
