#!/usr/bin/python
# -*- coding: utf-8 -*-

# Part of Softhealer Technologies.

from odoo import models, api
from datetime import date, datetime


class AdvanceInventoryReport(models.AbstractModel):

    _name = 'report.sh_all_in_one_stock_report.sh_advance_inventory_report'
    _description = 'Advance Inventory Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        sh_from_date = datetime.strptime(data['sh_from_date'],
                '%Y-%m-%d').date()
        sh_to_date = datetime.strptime(data['sh_to_date'], '%Y-%m-%d'
                ).date()
        sh_current_date = date.today()
        sh_product_id = data.get('sh_product_ids')
        if sh_product_id:
            sh_product_ids = self.env['product.product'
                    ].sudo().search([('id', 'in', sh_product_id)])
        else:
            sh_product_ids = self.env['product.product'
                    ].sudo().search([('id', '>', 0),('detailed_type', '=', 'product')])
        fsn_stock_list = []
        if sh_product_ids:
            for product in sh_product_ids:
                purchase_qty = 0
                sale_qty = 0
                negative_qty_open = 0
                negative_qty_close = 0
                positive_qty_open = 0
                positive_qty_close = 0
                purchase_qty_open = 0
                sale_qty_open = 0
                open_stock = 0
                close_stock = 0
                adjustment_done = False
                sales_stock = 0
                scrap_qty_open = 0.0
                scrap_qty_close = 0.0
                scrap_stock_open = False
                scrap_qty_close = False
                stock_quant_inventory = self.env['stock.quant'
                        ].sudo().search([('product_id', '=',
                        product.id), ('inventory_quantity', '=',
                        False)], order='id desc', limit=1)
                if stock_quant_inventory:
                    adjustment_done = True
                stock_move = self.env['stock.move'
                        ].sudo().search([('product_id', '=',
                        product.id), ('date', '>=', sh_from_date),
                        ('date', '<=', sh_current_date), ('state', '=',
                        'done'), ('scrapped', '=', False)])
                if stock_move:
                    if not  adjustment_done:
                        sale_order_domain_open = [('date', '>=',
                                sh_from_date), ('date', '<=',
                                sh_current_date), ('product_id', '=',
                                product.id), ('state', '=', 'done'),
                                ('move_id', 'in', stock_move.ids)]
                        sale_stock_order_open = \
                            self.env['stock.move.line'
                                ].sudo().search(sale_order_domain_open)
                        scrap_stock_open = self.env['stock.move'
                                ].sudo().search([('product_id', '=',
                                product.id), ('date', '>=',
                                sh_from_date), ('date', '<=',
                                sh_current_date), ('state', '=', 'done'
                                ), ('scrapped', '=', True)])
                        if scrap_stock_open:
                            for scrap in scrap_stock_open:
                                scrap_qty_open += scrap.product_uom_qty
                        if sale_stock_order_open:
                            for order in sale_stock_order_open:
                                if order.picking_id.picking_type_id.code \
                                    == 'incoming':
                                    purchase_qty_open += order.quantity
                                if order.picking_id.picking_type_id.code \
                                    == 'outgoing':
                                    sale_qty_open += order.quantity
                            open_stock = product.qty_available \
                                - purchase_qty_open + sale_qty_open \
                                + scrap_qty_open
                        if sh_to_date < sh_current_date:
                            sale_order_domain_close = [('date', '>',
                                    sh_to_date), ('date', '<=',
                                    sh_current_date), ('product_id', '='
                                    , product.id), ('state', '=', 'done'
                                    ), ('move_id', 'in',
                                    stock_move.ids)]
                            sale_stock_order_close = \
                                self.env['stock.move.line'
                                    ].sudo().search(sale_order_domain_close)
                            scrap_stock_close = self.env['stock.move'
                                    ].sudo().search([('product_id', '='
                                    , product.id), ('date', '>=',
                                    sh_to_date), ('date', '<=',
                                    sh_current_date), ('state', '=',
                                    'done'), ('scrapped', '=', True)])
                            if scrap_stock_close:
                                for scrap in scrap_stock_close:
                                    scrap_qty_close += \
    scrap.product_uom_qty
                            if sale_stock_order_close:
                                for order in sale_stock_order_close:
                                    if order.picking_id.picking_type_id.code \
    == 'incoming':
                                        purchase_qty += order.quantity
                                    if order.picking_id.picking_type_id.code \
    == 'outgoing':
                                        sale_qty += order.quantity
                                close_stock = product.qty_available \
                                    - purchase_qty + sale_qty \
                                    + scrap_qty_close
                            else:
                                close_stock = product.qty_available \
                                    + scrap_qty_close
                        else:
                            close_stock = product.qty_available
                    else:
                        stock_adjustment_negative_open = \
                            self.env['stock.move'].sudo().search([
                            ('product_id', '=', product.id),
                            ('is_inventory', '=', True),
                            ('state', '=', 'done'),
                            ('picking_id', '=', False),
                            ('location_id.usage', '=', 'internal'),
                            ('location_dest_id.usage', '=', 'inventory'
                             ),
                            ('date', '>=', sh_from_date),
                            ('date', '<=', sh_current_date),
                            ])
                        stock_adjustment_negative_close = \
                            self.env['stock.move'].sudo().search([
                            ('product_id', '=', product.id),
                            ('is_inventory', '=', True),
                            ('state', '=', 'done'),
                            ('picking_id', '=', False),
                            ('location_id.usage', '=', 'internal'),
                            ('location_dest_id.usage', '=', 'inventory'
                             ),
                            ('date', '>', sh_to_date),
                            ('date', '<=', sh_current_date),
                            ])
                        stock_adjustment_positive_open = \
                            self.env['stock.move'].sudo().search([
                            ('product_id', '=', product.id),
                            ('is_inventory', '=', True),
                            ('state', '=', 'done'),
                            ('picking_id', '=', False),
                            ('location_id.usage', '=', 'inventory'),
                            ('location_dest_id.usage', '=', 'internal'
                             ),
                            ('date', '>=', sh_from_date),
                            ('date', '<=', sh_current_date),
                            ])
                        stock_adjustment_positive_close = \
                            self.env['stock.move'].sudo().search([
                            ('product_id', '=', product.id),
                            ('is_inventory', '=', True),
                            ('state', '=', 'done'),
                            ('picking_id', '=', False),
                            ('location_id.usage', '=', 'inventory'),
                            ('location_dest_id.usage', '=', 'internal'
                             ),
                            ('date', '>', sh_to_date),
                            ('date', '<=', sh_current_date),
                            ])
                        for adjustment in stock_adjustment_negative_open:
                            negative_qty_open += adjustment.product_uom_qty
                        for adjustment in stock_adjustment_negative_close:
                            negative_qty_close +=  adjustment.product_uom_qty
                        for adjustment in stock_adjustment_positive_open:
                            positive_qty_open +=  adjustment.product_uom_qty
                        for adjustment in stock_adjustment_positive_close:
                            positive_qty_close += adjustment.product_uom_qty
                        sale_order_domain_open = [('date', '>=',
                                sh_from_date), ('date', '<=',
                                sh_current_date), ('product_id', '=',
                                product.id), ('state', '=', 'done'),
                                ('move_id', 'in', stock_move.ids)]
                        sale_stock_order_open = \
                            self.env['stock.move.line'
                                ].sudo().search(sale_order_domain_open)
                        scrap_stock_open = self.env['stock.move'
                                ].sudo().search([('product_id', '=',
                                product.id), ('date', '>=',
                                sh_from_date), ('date', '<=',
                                sh_current_date), ('state', '=', 'done'
                                ), ('scrapped', '=', True)])
                        if scrap_stock_open:
                            for scrap in scrap_stock_open:
                                scrap_qty_open += scrap.product_uom_qty
                        if sale_stock_order_open:
                            for order in sale_stock_order_open:
                                if order.picking_id.picking_type_id.code \
                                    == 'incoming':
                                    purchase_qty_open += order.quantity
                                if order.picking_id.picking_type_id.code \
                                    == 'outgoing':
                                    sale_qty_open += order.quantity
                            open_stock = product.qty_available \
                                - purchase_qty_open + sale_qty_open \
                                - positive_qty_open + negative_qty_open \
                                + scrap_qty_open
                        if sh_to_date < sh_current_date:
                            sale_order_domain_close = [('date', '>',
                                    sh_to_date), ('date', '<=',
                                    sh_current_date), ('product_id', '='
                                    , product.id), ('state', '=', 'done'
                                    ), ('move_id', 'in',
                                    stock_move.ids)]
                            sale_stock_order_close = \
                                self.env['stock.move.line'
                                    ].sudo().search(sale_order_domain_close)
                            scrap_stock_close = self.env['stock.move'
                                    ].sudo().search([('product_id', '='
                                    , product.id), ('date', '>=',
                                    sh_to_date), ('date', '<=',
                                    sh_current_date), ('state', '=',
                                    'done'), ('scrapped', '=', True)])
                            if scrap_stock_close:
                                for scrap in scrap_stock_close:
                                    scrap_qty_close += scrap.product_uom_qty
                            if sale_stock_order_close:
                                for order in sale_stock_order_close:
                                    if order.picking_id.picking_type_id.code == 'incoming':
                                        purchase_qty += order.quantity
                                    if order.picking_id.picking_type_id.code == 'outgoing':
                                        sale_qty += order.quantity
                                close_stock = product.qty_available - purchase_qty + sale_qty - positive_qty_close + negative_qty_close + scrap_qty_close
                            else:
                                close_stock = product.qty_available \
                                    - positive_qty_close \
                                    + negative_qty_close \
                                    + scrap_qty_close
                        else:
                            close_stock = product.qty_available \
                                - positive_qty_close \
                                + negative_qty_close
                elif sh_from_date > sh_current_date and sh_to_date \
                    > sh_current_date:
                    open_stock = product.qty_available
                    close_stock = product.qty_available
                sale_order_line_domain = [('order_id.date_order', '>=',
                        sh_from_date), ('order_id.date_order', '<=',
                        sh_to_date), ('product_id', '=', product.id),
                        ('order_id.state', '=', 'sale')]

                sales_lines = self.env['sale.order.line'
                        ].sudo().search(sale_order_line_domain)
                for lines in sales_lines:
                    sales_stock += lines.product_uom_qty

                avg_stock = (open_stock + close_stock) / 2
                if avg_stock > 0:
                    turn_over_ratio = sales_stock / avg_stock
                else:
                    turn_over_ratio = sales_stock
                if turn_over_ratio < 1:
                    fsn = 'N'
                elif turn_over_ratio >= 1 and turn_over_ratio <= 3:
                    fsn = 'S'
                else:
                    fsn = 'F'
                vals = {
                    'product': product.name,
                    'open_stock': open_stock,
                    'close_stock': close_stock,
                    'avg_stock': avg_stock,
                    'sale_qty': sales_stock,
                    'turn_over_ratio': round(turn_over_ratio, 2),
                    'fsn': fsn,
                    }
                fsn_stock_list.append(vals)
        return {'fsn_stock_list': fsn_stock_list}
