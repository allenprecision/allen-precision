# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api,_
from xlwt.Style import easyfont
from odoo.exceptions import UserError
from datetime import timedelta

class NonMovingProduct(models.Model):
    _name = 'sh.non.moving.product'
    _description = 'Non Moving Product'
    
    product_id = fields.Many2one(
        string='Product Name',comodel_name='product.product')
    default_code=fields.Char(string="Product Code")
    onhand_qty = fields.Float(string='OnHand Qty.')
    sh_last_sale = fields.Date(string='Last Sales')
    sh_no_picking = fields.Boolean(string="No Picking")
    