# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import html_translate

class ProductBrand(models.Model):
    _name = "as.product.brand"
    _inherit = ["website.multi.mixin", "website.searchable.mixin",'image.mixin']
    _description = "Product Brands"
    _order = "sequence,id"

    active = fields.Boolean(default=True)
    sequence = fields.Integer()
    logo = fields.Binary(string="Logo", required=True)
    set_image_mixin = fields.Boolean(compute="_get_logo", store=True)
    name = fields.Char(string="Name", translate=True, required=True)
    brand_description = fields.Text(string="Short Description", translate=True)
    description = fields.Html(string="Detail Description", translate=html_translate)
    brand_product_ids = fields.One2many("product.template","product_brand_id", string="Products",)
    products_count = fields.Integer(string="Number of products", compute="_get_products_count")
    
    _sql_constraints = [("name_uniqe", "unique (name)", "Brand name already exists.!")]

    @api.depends("logo")
    def _get_logo(self):
        for rec in self:
            rec.image_1920 = rec.logo
            rec.set_image_mixin = True

    @api.depends("brand_product_ids")
    def _get_products_count(self):
        " Product count brandwise "
        self.products_count = len(self.brand_product_ids)

    def as_brand_product(self):
        " Brand page redirector "
        result = {
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "domain": [["product_brand_id", "=", self.id]],
            "name": "Products",
            "view_mode": "kanban,tree,form",
        }
        return result

class ProductTemplateExtend(models.Model):
    _inherit = "product.template"

    product_brand_id = fields.Many2one("as.product.brand", string="Brand", help="Select a brand for this product")