# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    last_so_date = fields.Datetime(compute='_compute_get_last_so', string='Last SO Date')
    last_po_date = fields.Datetime(compute='_compute_get_last_po', string='Last PO Date')
    so_id = fields.Many2one('sale.order', string='SO')
    po_id = fields.Many2one('purchase.order', string='PO')

    def _compute_get_last_so(self):
        self.last_so_date = False
        for partner in self:
            last_so = self.env['sale.order'].search([('partner_id', '=', partner.id), ('state', 'not in', ['draft', 'sent', 'cancel'])], order='date_order desc', limit=1)
            if last_so:
                partner.last_so_date = last_so.date_order
                partner.so_id = last_so.id

    def _compute_get_last_po(self):
        self.last_po_date = False
        for partner in self:
            last_po = self.env['purchase.order'].search([('partner_id', '=', partner.id), ('state', 'not in', ['draft', 'sent', 'cancel'])], order='date_order desc', limit=1)
            if last_po:
                partner.last_po_date = last_po.date_order
                partner.po_id = last_po.id
