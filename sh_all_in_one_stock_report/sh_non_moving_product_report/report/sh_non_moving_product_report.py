# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, api,_
from odoo.exceptions import UserError
from datetime import timedelta
from datetime import datetime

class Non_Moving_Product(models.AbstractModel):
    _name = 'report.sh_all_in_one_stock_report.sh_non_moving_product'
    _description = 'Non Moving Product Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        ''' Prepare values for print Non Moving Product report'''
        data = dict(data or {})
        
        # ========== Get value from wizard =================
        
        sh_from_date = datetime.strptime(
            data['sh_from_date'], '%Y-%m-%d').date()
        sh_to_date = datetime.strptime(
            data['sh_to_date'], '%Y-%m-%d').date()
        sh_selection = data.get('sh_selection')
        sh_location_ids = self.env['stock.location'].sudo().search(
            [('id', 'in', data.get('sh_location_ids'))])
        sh_warehouse_id=False
        if data.get('sh_warehouse_id'):
            sh_warehouse_id = self.env['stock.warehouse'].sudo().search(
                [('id', '=', data.get('sh_warehouse_id')[0])])
        sh_product_ids = self.env['product.product'].sudo().search(
            [('id', 'in', data.get('sh_product_ids'))])
        non_move_stock=[]
        location_name=''
        
        # ========== Filter Product wise report =================
        
        if sh_product_ids:
            products=sh_product_ids
        else:
            products=self.env['product.product'].search([('detailed_type','=','product')])
            
        # ========== Print selected warehouse wise report  =================
        if sh_selection=='warehouse':
            self._cr.execute('''select id from stock_picking where 
            date_done>=%s and date_done<=%s and location_id IN %s
            and state='done'and picking_type_id IN
            (select id from stock_picking_type where code='outgoing')''',
            [str(sh_from_date),str(sh_to_date),tuple([sh_warehouse_id.lot_stock_id.id]+sh_warehouse_id.lot_stock_id.child_internal_location_ids.ids)])
            picking_dict = self._cr.dictfetchall()
            
        # ========== Print selected location wise report =================
        elif sh_selection=='location':
            if sh_location_ids:
                sh_location_ids=sh_location_ids
            else:
                sh_location_ids=self.env['stock.location'].sudo().search([('usage','=','internal')])
            self._cr.execute('''select id from stock_picking where 
            date_done>=%s and date_done<=%s and location_id IN %s and state='done'and picking_type_id IN
            (select id from stock_picking_type where code='outgoing')''',
            [str(sh_from_date),str(sh_to_date),tuple(sh_location_ids.ids)])
            picking_dict = self._cr.dictfetchall()
            location_name=','.join(sh_location_ids.mapped('complete_name'))
        
        # ========== Prepare vals for print report  =================
        
        if picking_dict:
            picking= self.env['stock.picking'].browse([r['id'] for r in picking_dict])
            if picking:
                for product in products:
                    self._cr.execute('''select id from stock_move where product_id=%s and picking_id IN %s ''',[str(product.id),tuple(picking.ids)])
                    stock_move = self._cr.dictfetchall()
                    if stock_move:
                        pass
                    else:
                        self._cr.execute('''select id from stock_move where product_id=(%s) and picking_id in (select id from stock_picking where picking_type_id IN
                        (select id from stock_picking_type where code='outgoing')) and state='done' ORDER BY id DESC LIMIT 1 ''',[product.id])
                        stock_move = self._cr.dictfetchall()
                        if sh_selection=='warehouse':
                            quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.warehouse_id.id == sh_warehouse_id.id).mapped('quantity'))
                        elif sh_selection=='location':
                            quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.id in sh_location_ids.ids).mapped('quantity'))      
                        if stock_move:
                            moves = self.env['stock.move'].sudo().browse([r['id'] for r in stock_move])
                            non_move_stock.append([product.display_name,product.default_code,quantity,moves.date.date()])
                        else:
                            non_move_stock.append([product.display_name,product.default_code,quantity,''])
            else:
                for product in products:
                    self._cr.execute('''select id from stock_move where product_id=(%s) and picking_id in (select id from stock_picking where picking_type_id IN
                    (select id from stock_picking_type where code='outgoing')) and state='done' ORDER BY id DESC LIMIT 1 ''',[product.id])
                    stock_move = self._cr.dictfetchall()
                    if sh_selection=='warehouse':
                        quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.warehouse_id.id == sh_warehouse_id.id).mapped('quantity'))
                    elif sh_selection=='location':
                        quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.id in sh_location_ids.ids).mapped('quantity'))      
                    if stock_move:
                        moves = self.env['stock.move'].sudo().browse([r['id'] for r in stock_move])
                        non_move_stock.append([product.display_name,product.default_code,quantity,moves.date.date()])
                    else:
                        non_move_stock.append([product.display_name,product.default_code,quantity,''])
        else:
            for product in products:
                self._cr.execute('''select id from stock_move where product_id=(%s) and picking_id in (select id from stock_picking where picking_type_id IN
                (select id from stock_picking_type where code='outgoing')) and state='done' ORDER BY id DESC LIMIT 1 ''',[product.id])
                stock_move = self._cr.dictfetchall()
                if sh_selection=='warehouse':
                    quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.warehouse_id.id == sh_warehouse_id.id).mapped('quantity'))
                elif sh_selection=='location':
                    quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.id in sh_location_ids.ids).mapped('quantity'))      
                if stock_move:
                    moves = self.env['stock.move'].sudo().browse([r['id'] for r in stock_move])
                    non_move_stock.append([product.display_name,product.default_code,quantity,moves.date.date()])
                else:
                    non_move_stock.append([product.display_name,product.default_code,quantity,''])
        # Return Preparing values
        if non_move_stock:
            return{
                'non_move_stock': non_move_stock,
                'sh_from_date': sh_from_date,
                'sh_to_date': sh_to_date,
                'location_name': location_name if location_name else '',
                'sh_warehouse':sh_warehouse_id.name if sh_warehouse_id else '',
                'sh_selection':sh_selection,
            }
        else:
            raise UserError(_('No Records Found..'))
