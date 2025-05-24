# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools.translate import html_translate

class ProductTabs(models.Model):
    _name = 'as.product.tab'
    _description = 'Product Tabs'
    _order = 'sequence, id'

    product_id = fields.Many2one('product.template', string='Product Template')
    tab_name = fields.Char(string='Tab Name', translate=True, required=True)
    tab_content = fields.Html(string='Tab Content', translate=html_translate, sanitize_attributes=False)
    website_ids = fields.Many2many('website', help='Description For specific website.')
    sequence = fields.Integer(string='Sequence', default=1, help='Sequence order for display.')

class ProductTabLine(models.Model):
    _name = 'product.tab.line'
    _description = 'Product Label Line'
    _order = 'sequence, id'

    product_id = fields.Many2one('product.template', string='Product Template')
    tab_name = fields.Char(string='Tab Name', translate=True, required=True)
    tab_content = fields.Html(string='Tab Content', translate=html_translate, sanitize_attributes=False)
    website_ids = fields.Many2many('website', help='You can set the description in particular website.')
    sequence = fields.Integer(string='Sequence', default=1, help='Gives the sequence order when displaying.')

    def getTab(self, currentWebsite, tabWebsiteArray):
        ''' Tab checker website wise '''
        if currentWebsite in tabWebsiteArray or len(tabWebsiteArray) == 0:
            return True
        else:
            return False

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pro_tab_ids = fields.One2many('as.product.tab', 'product_id', string='Product Tabs', help='Set the product tabs')