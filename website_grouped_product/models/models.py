# -*- coding: utf-8 -*-

from odoo import models, fields, api


class GroupProduct(models.Model):
    _name = "product.combo"
    _order = "sequence,id"
    _description = "Product packs"

    @api.onchange('product_id')
    def product_id_onchange(self):
        return {'domain': {'product_id': [('is_combo', '=', False)]}}

    sequence = fields.Integer(string="Sequence")
    name = fields.Char('name', translate=True)
    product_template_id = fields.Many2one(
        'product.template', 'Item', domain=[('is_combo', '=', True)])
    product_quantity = fields.Float('Quantity',  digits='Product Unit of Measure', default=1.0)
    product_id = fields.Many2one(
        'product.product', 'Product', required=True)
    price = fields.Float(
        'Price', related='product_id.lst_price', translate=True)


class Product(models.Model):
    _inherit = "product.product"

    parent_ids = fields.One2many('product.combo', 'product_id')
    is_group_item = fields.Boolean('Is Group Item', default=False)


class ComboProductTemplate(models.Model):
    _inherit = "product.template"

    is_combo = fields.Boolean('Group Product', default=False)
    combo_product_id = fields.One2many(
        'product.combo', 'product_template_id', 'Group Item')

    @api.onchange('is_combo')
    def _onchange_combo(self):
        self.ensure_one()
        if self.is_combo and self.type != 'consu':
            self.type = 'consu'

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, parent_combination=False, only_template=False):
        return super(ComboProductTemplate, self)._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty,
            parent_combination=parent_combination, only_template=only_template)
