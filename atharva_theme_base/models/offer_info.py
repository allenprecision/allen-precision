# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools.translate import html_translate

class ProductOffer(models.Model):
    _name = "as.product.extra.info"
    _description = "Product Offer and Attributes Information"

    sequence = fields.Integer(string="Sequence")
    types = fields.Selection([('offer','Product'),('attrib','Attribute')],
                            required=True, string="Information For", default="offer")
    icon = fields.Char(default="tags")
    name = fields.Char(translate=True, required=True)
    short_description = fields.Char(string="Description", translate=True)
    detail_description = fields.Html(translate=html_translate, sanitize_form=False, sanitize_attributes=False)
    product_ids = fields.Many2many("product.template", string="Products")

    def as_product_info_design(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/advance/info/editor/%s?enable_editor=1' % (self.id),
            'target': 'new',
        }

class ProductAttributeExtend(models.Model):
    _inherit = 'product.attribute'

    attribute_extra_info_id = fields.Many2one("as.product.extra.info",
        string="Details Information", domain='[("types", "=", "attrib")]',
        help="You can show detail information about the attribute by selecting product advance information object.")

class ProductTemplateInfo(models.Model):
    _inherit = 'product.template'

    product_offer_ids = fields.Many2many("as.product.extra.info", string="Advance Information",
    help="You can display some offer or discount with product advance information object.")
