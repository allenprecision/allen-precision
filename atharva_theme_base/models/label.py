# -*- coding: utf-8 -*-

from odoo import fields, models

class ProductLabel(models.Model):
    _name = 'as.product_label'
    _description = 'Product Label'

    name = fields.Char(string='Name', required=True, translate=True, help='Name of the label')
    label_text_color = fields.Char(string='Text Color',
        help='Select a Individual HTML Color code (e.g. #ff0000) to display the color of label text.')
    label_color = fields.Char( string='Color',
        help='Select a Individual HTML Color code (e.g. #ff0000) to display the color of label.')
    label_option = fields.Selection([
        ('option_1', 'Option 1'),
        ('option_2', 'Option 2'),
        ('option_3', 'Option 3'),
        ('option_4', 'Option 4'),
        ('option_5', 'Option 5')
    ], string='Select the Option for label', required=True, default='option_1', readonly=False)

class ProductLabelLine(models.Model):
    _name = 'as.product_label.line'
    _description = 'Product Template Label Line'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template Id', required=True)
    website_id = fields.Many2one('website', string='Website', required=True)
    label = fields.Many2one('as.product_label', required=True, string='Label', help='Name of the product label')

    _sql_constraints = [('unique_product_label', 'unique(product_tmpl_id, website_id)',
                         'Website must be unique!')]

class ProductTemplateLabelExtend(models.Model):
    _inherit = 'product.template'

    pro_label_line_ids = fields.One2many('as.product_label.line', 'product_tmpl_id',
    string='Product Labels', help='Set the product labels')