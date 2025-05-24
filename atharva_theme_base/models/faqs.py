# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductFAQ(models.Model):
    _name = "product.faqs"
    _description = "Product FAQs"
    _order = "sequence, id"
    _rec_name = "id"

    sequence = fields.Integer(default=10)
    question = fields.Char(string="Question", required=True, translate=True)
    answer = fields.Text(string="Answer", required=True, translate=True)
    products = fields.Many2many('product.template', string="Products")
    website_ids = fields.Many2many('website', help='Description For specific website.')