# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_last_so_date = fields.Datetime(compute='_compute_get_last_so', string='Last SO Date')
    product_last_po_date = fields.Datetime(compute='_compute_get_last_po', string='Last PO Date')
    last_so_id = fields.Many2one('sale.order', string='Last SO')
    last_po_id = fields.Many2one('purchase.order', string='Last PO')

    def _compute_get_last_so(self):
        self.product_last_so_date = False
        for product in self:
            last_so_line = self.env['sale.order.line'].search([('product_id', '=', product.id), ('state', 'not in', ['draft', 'sent', 'cancel'])], order='id desc', limit=1)
            if last_so_line:
                product.product_last_so_date = last_so_line.order_id.date_order
                product.last_so_id = last_so_line.order_id.id

    def _compute_get_last_po(self):
        self.product_last_po_date = False
        for product in self:
            last_po_line = self.env['purchase.order.line'].search([('product_id', '=', product.id), ('state', 'not in', ['draft', 'sent', 'cancel'])], order='id desc', limit=1)
            if last_po_line:
                product.product_last_po_date = last_po_line.order_id.date_order
                product.last_po_id = last_po_line.order_id.id
