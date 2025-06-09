# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, api,_,fields
from datetime import date, datetime,timedelta
from odoo.exceptions import UserError
from odoo.http import request
import pytz

class StockCardReport(models.AbstractModel):
    _name = 'report.sh_all_in_one_stock_report.sh_inventory_card_report'
    _description = 'Stock Card Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        ''' Prepare values for print stock card report'''
        data = dict(data or {})

        # Getting Value form wizard

        sh_from_date = datetime.strptime(
            data['sh_from_date'], '%Y-%m-%d').date()
        sh_to_date = datetime.strptime(
            data['sh_to_date'], '%Y-%m-%d').date()
        sh_current_date = date.today()
        sh_current_date = datetime.combine(sh_current_date, datetime.min.time())+timedelta(days=1)
        sh_from_datetime=datetime.combine(sh_from_date, datetime.min.time())
        sh_to_datetime=datetime.combine(sh_to_date, datetime.min.time())+timedelta(days=1)
        user_tz = pytz.timezone(request.env.context.get('tz') or request.env.user.tz or 'UTC')
        today = user_tz.localize(fields.Datetime.from_string(str(sh_from_datetime)))
        sh_from_datetime = today.astimezone(pytz.timezone('UTC'))
        sh_from_datetime = datetime.strptime(str(sh_from_datetime)[:19], "%Y-%m-%d %H:%M:%S")
        today = user_tz.localize(fields.Datetime.from_string(str(sh_to_datetime)))
        sh_to_datetime = today.astimezone(pytz.timezone('UTC'))
        sh_to_datetime = datetime.strptime(str(sh_to_datetime)[:19], "%Y-%m-%d %H:%M:%S")
        today = user_tz.localize(fields.Datetime.from_string(str(sh_current_date)))
        sh_current_date = today.astimezone(pytz.timezone('UTC'))
        sh_company_id = self.env['res.company'].sudo().search(
            [('id', '=', data.get('sh_company_id')[0])])
        sh_warehouse_id = self.env['stock.warehouse'].sudo().search(
            [('id', '=', data.get('sh_warehouse_id')[0])])
        sh_location_id = self.env['stock.location'].sudo().search(
            [('id', '=', data.get('sh_location_id')[0])])
        sh_category_ids = data.get('sh_category_ids')
        sh_product_ids = data.get('sh_product_ids')
        sh_select_product_cat = data.get('sh_select_product_cat')
        user = self.env.user
        category_list = []
        product_dict = {}
        stock_card_dict = {}
        product_list = []
        # Prepare dictionary category wise
        if sh_select_product_cat == 'category':

            if len(sh_category_ids) > 0:
                sh_category = self.env['product.category'].sudo().search(
                    [('id', 'in', sh_category_ids)])
            else:
                sh_category = self.env['product.category'].sudo().search([
                    ('id', '>', 0)])
            for category in sh_category:
                product_dict[category.display_name] = []
                stock_card_dict[category.display_name] = {}
                sh_products = self.env['product.product'].sudo().search(
                    [('categ_id', '=', category.id), ('detailed_type', '=', 'product')])
                if sh_products:
                    for product in sh_products:
                        move_date = False
                        origin = False
                        in_qty = 0.0
                        out_qty = 0.0
                        close_stock = 0.0
                        open_stock = 0.0
                        lines_list = []
                        total_out_qty = 0.0
                        total_in_qty = 0.0
                        transfer = 0.0
                        onhand = 0.0
                        # Calculate Opeing Balance
                        
                        # ================================================
                        # CHECK POS MODULE IS INSTALLED OR NOT  
                        # ================================================
                        pos_return_picking=[]
                        pos_r_qty_open=0
                        is_pos_installed = self.env['ir.module.module'].sudo().search(
                            [('name', '=', 'point_of_sale'),('state','=','installed')], limit=1)
                        if is_pos_installed:
                            # ================================================
                            # Calculate pos return qty 
                            # ================================================
                            
                            self._cr.execute('''select id,qty from pos_order_line where product_id = %s and qty<0 and order_id IN (select id from pos_order where date_order>= %s and date_order<= %s and state IN ('paid','done','invoiced'))''',
                                [product.id,str(sh_from_date),str(sh_current_date)])
                            pos_r_qty_open = self._cr.dictfetchall()
                            pos_r_qty_open = sum([sub['qty'] for sub in pos_r_qty_open])
                        
                            self._cr.execute('''select id,qty,order_id from pos_order_line where product_id = %s and qty<0 and order_id IN 
                                (select id from pos_order where date_order>= %s and date_order<= %s and state IN ('paid','done','invoiced'))''',
                                [product.id,str(sh_from_date),str(sh_current_date)])
                            pos_return_order = self._cr.dictfetchall()
                            pos_return_picking = self.env['pos.order'].sudo().browse([r['order_id'] for r in pos_return_order]).mapped('picking_ids').mapped('id')
                        sale_order_domain_open = [
                            ('product_id', '=', product.id),
                            ('date', '>=', sh_from_datetime),
                            ('date', '<=', sh_current_date),
                            ('state', '=', 'done'),
                            ('company_id', '=', sh_company_id.id),
                            ('picking_id','not in',pos_return_picking),
                            '|',
                            ('location_id', '=', sh_location_id.id),
                            ('location_dest_id', '=', sh_location_id.id)
                        ]
                        sale_stock_order_open = self.env['stock.move.line'].sudo().search(
                            sale_order_domain_open)
                        product_onhand = self.env['stock.quant'].sudo().search(
                            [('location_id', '=', sh_location_id.id), ('product_id', '=', product.id)], limit=1)
                        if product_onhand:
                            onhand = product_onhand.quantity
                        if sale_stock_order_open:
                            for order in sale_stock_order_open:
                                if order.location_id.id != order.location_dest_id.id :
                                    if order.product_uom_id.id != order.product_id.uom_id.id:
                                        qty_done = order.product_uom_id.sh_compute_quantity(order.quantity, order.product_id.uom_id)
                                    else:
                                        qty_done = order.quantity
                                    if order.location_id.id == sh_location_id.id:
                                        transfer += qty_done
                                    elif order.location_dest_id.id == sh_location_id.id:
                                        transfer -= qty_done
                        open_stock = onhand+transfer+pos_r_qty_open

                        # Display Movement of Product in Stock (Sale , Purhcase , Internal Transfer , Adjustment , Scrap)

                        stock_move = self.env['stock.move.line'].sudo().search(
                            [('product_id', '=', product.id), ('date', '>=', sh_from_date), ('date', '<=', sh_to_date), ('state', '=', 'done'), ('company_id', '=', sh_company_id.id), '|', ('location_id', '=', sh_location_id.id), ('location_dest_id', '=', sh_location_id.id)], order='date asc')
                        if stock_move:
                            for move in stock_move:
                                if move.location_id.id != move.location_dest_id.id :
                                    in_qty = 0.0
                                    out_qty = 0.0
                                    move_date = move.date
                                    balance = 0.0
                                    origin = move.origin

                                    if not move.origin and move.picking_code:
                                        origin = move.reference
                                    elif not move.origin and not move.picking_code:
                                        origin = 'Inventory Adjustment'
                                    if move.location_id.id == sh_location_id.id:
                                        total_out_qty += move.quantity
                                        out_qty = move.quantity
                                    elif move.location_dest_id.id == sh_location_id.id:
                                        total_in_qty += move.quantity
                                        in_qty = move.quantity
                                    lines_list.append(
                                        [move_date.date(), origin, in_qty, out_qty, balance])
                            for index in range(0, len(lines_list)):
                                if lines_list[index-1]:
                                    lines_list[index][4] = lines_list[index-1][4] + \
                                        lines_list[index][2] - \
                                        lines_list[index][3]
                                else:
                                    lines_list[index][4] = lines_list[index][2] - \
                                        lines_list[index][3]
                                if index == 0:
                                    lines_list[0][4] += open_stock
                        if len(lines_list) < 1:
                            close_stock = open_stock
                        else:
                            close_stock = lines_list[-1][-1]

                        if open_stock or lines_list or total_in_qty or total_out_qty or close_stock:
                            product_dict[category.display_name].append(
                                product.display_name)
                            stock_card_dict[category.display_name][product.display_name] = {
                                'open_stock': open_stock, 'lines': lines_list, 'total': ['', 'TOTAL', total_in_qty, total_out_qty, close_stock]}
                if len(product_dict[category.display_name]) > 0:
                    category_list.append(category.display_name)
                if not stock_card_dict[category.display_name]:
                    del stock_card_dict[category.display_name]

        # Prepare dictionary Product wise

        elif sh_select_product_cat == 'product':

            if sh_product_ids:
                sh_products = self.env['product.product'].sudo().search(
                    [('id', 'in', sh_product_ids), ('detailed_type', '=', 'product')])
            else:
                sh_products_get = self.env['stock.quant'].sudo().search(
                    [('location_id', '=', sh_location_id.id)])
                sh_products_get = sh_products_get.mapped('product_id')
                sh_products = self.env['product.product'].sudo().search(
                    [('id', 'in', sh_products_get.ids), ('detailed_type', '=', 'product'), '|', ('company_id', '=', sh_company_id.id), ('company_id', '=', False)])
            if sh_products:
                for product in sh_products:
                    move_date = False
                    origin = False
                    in_qty = 0.0
                    out_qty = 0.0
                    open_stock = 0.0
                    lines_list = []
                    total_out_qty = 0.0
                    total_in_qty = 0.0
                    close_stock = 0.0
                    transfer = 0.0
                    onhand = 0.0
                    # Calculate Opeing Balance
                    
                    # ================================================
                    # CHECK POS MODULE IS INSTALLED OR NOT  
                    # ================================================
                    pos_return_picking=[]
                    pos_r_qty_open=0
                    is_pos_installed = self.env['ir.module.module'].sudo().search(
                        [('name', '=', 'point_of_sale'),('state','=','installed')], limit=1)
                    if is_pos_installed:
                        # ================================================
                        # Calculate pos return qty 
                        # ================================================
                        self._cr.execute('''select id,qty from pos_order_line where product_id = %s and qty<0 and order_id IN (select id from pos_order where date_order>= %s and date_order<= %s and state IN ('paid','done','invoiced'))''',
                            [product.id,str(sh_from_date),str(sh_current_date)])
                        pos_r_qty_open = self._cr.dictfetchall()
                        pos_r_qty_open=sum([sub['qty'] for sub in pos_r_qty_open ])
                    
                        self._cr.execute('''select id,qty,order_id from pos_order_line where product_id = %s and qty<0 and order_id IN 
                            (select id from pos_order where date_order>= %s and date_order<= %s and state IN ('paid','done','invoiced'))''',
                            [product.id,str(sh_from_date),str(sh_current_date)])
                        pos_return_order = self._cr.dictfetchall()
                        pos_return_picking= self.env['pos.order'].sudo().browse([r['order_id'] for r in pos_return_order]).mapped('picking_ids').mapped('id')
                    sale_order_domain_open = [
                        ('product_id', '=', product.id),
                        ('date', '>=', sh_from_datetime),
                        ('date', '<=', sh_current_date),
                        ('state', '=', 'done'),
                        ('company_id', '=', sh_company_id.id),
                        ('picking_id','not in',pos_return_picking),
                        '|',
                        ('location_id', '=', sh_location_id.id),
                        ('location_dest_id', '=', sh_location_id.id)
                    ]
                    sale_stock_order_open = self.env['stock.move.line'].sudo().search(
                        sale_order_domain_open)
                    product_onhand = self.env['stock.quant'].sudo().search(
                        [('location_id', '=', sh_location_id.id), ('product_id', '=', product.id)], limit=1)
                    if product_onhand:
                        onhand = product_onhand.quantity                    
                    if sale_stock_order_open:
                        for order in sale_stock_order_open:
                            if order.location_id.id != order.location_dest_id.id :
                                if order.product_uom_id.id != order.product_id.uom_id.id:
                                    qty_done = order.product_uom_id.sh_compute_quantity(order.quantity, order.product_id.uom_id)
                                else:
                                    qty_done = order.quantity
                                if order.location_id.id == sh_location_id.id:
                                    transfer += qty_done
                                elif order.location_dest_id.id == sh_location_id.id:
                                    transfer -= qty_done
                        open_stock = onhand+transfer+pos_r_qty_open
                    # Display Movement of Product in Stock (Sale , Purhcase , Internal Transfer , Adjustment , Scrap)

                    stock_move = self.env['stock.move.line'].sudo().search(
                        [('product_id', '=', product.id),
                         ('date', '>=', sh_from_date),
                         ('date', '<=', sh_to_date),
                         ('state', '=', 'done'),
                         ('company_id', '=', sh_company_id.id),
                         '|',
                         ('location_id', '=', sh_location_id.id),
                         ('location_dest_id', '=', sh_location_id.id)
                         ], order='date asc')
                    if stock_move:
                        for move in stock_move:
                            if move.location_id.id != move.location_dest_id.id :
                                in_qty = 0.0
                                out_qty = 0.0
                                move_date = move.date
                                balance = 0.0
                                origin = move.origin
                                if not move.origin and move.picking_code:
                                    origin = move.reference
                                elif not move.origin and not move.picking_code:
                                    origin = 'Inventory Adjustment'
                                if move.location_id.id == sh_location_id.id:
                                    total_out_qty += move.quantity
                                    out_qty = move.quantity
                                elif move.location_dest_id.id == sh_location_id.id:
                                    total_in_qty += move.quantity
                                    in_qty = move.quantity
                                lines_list.append(
                                    [move_date.date(), origin, in_qty, out_qty, balance])
                        for index in range(0, len(lines_list)):
                            if lines_list[index-1]:
                                lines_list[index][4] = lines_list[index-1][4] + \
                                    lines_list[index][2]-lines_list[index][3]
                            else:
                                lines_list[index][4] = lines_list[index][2] - \
                                    lines_list[index][3]
                            if index == 0:
                                lines_list[0][4] += open_stock
                    if len(lines_list) < 1:
                        close_stock = open_stock
                    else:
                        close_stock = lines_list[-1][-1]
                    
                    if open_stock or lines_list or total_in_qty or total_out_qty or close_stock:
                        product_list.append(product.display_name)
                        stock_card_dict[product.display_name] = {'open_stock': open_stock, 'lines': lines_list, 'total': [
                            '', 'TOTAL', total_in_qty, total_out_qty, close_stock]}

        # Return Preparing values
        if stock_card_dict:
            return{
                'sh_from_date': sh_from_date,
                'sh_to_date': sh_to_date,
                'product_list': product_list,
                'product_dict': product_dict,
                'stock_card_dict': stock_card_dict,
                'sh_warehouse_id': sh_warehouse_id.name,
                'sh_location_id': sh_location_id.complete_name,
                'user_name': user.name,
                'category_list': category_list,
                'sh_select_product_cat': sh_select_product_cat,
            }
        else:
            raise UserError(_('No Data Found .....'))
