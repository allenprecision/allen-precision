# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api,_
from xlwt.Style import easyfont
from odoo.exceptions import UserError
from datetime import timedelta,datetime
import xlwt
import base64
import io

class NonMovingProductWizard(models.TransientModel):
    _name = 'sh.non.moving.product.report.wizard'
    _description = 'Non Moving Product wizard'

    sh_from_date = fields.Date(string='From Date', required=True)
    sh_to_date = fields.Date(string='To Date', required=True)
    sh_selection=fields.Selection([('warehouse', 'Warehouse'), ('location', 'location')],default='warehouse',required=True,string="Selection")
    sh_location_ids = fields.Many2many(comodel_name='stock.location', string='Location',
        domain=[('usage','=','internal')])
    sh_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string='Warehouse')
    sh_product_ids = fields.Many2many(
        comodel_name='product.product', string='Product',
        domain=[('detailed_type','=','product')])

    @api.onchange('sh_from_date', 'sh_to_date')
    def onchange_check_date(self):
        ''' Validation You can only select to-date greater than From-date '''
        if self.sh_from_date and self.sh_to_date:
            if self.sh_from_date > self.sh_to_date:
                raise UserError('From date must be less than To date.')

    def sh_print_stock_report(self):
        '''Call action of qweb pdf report.'''
        datas = self.read()[0]
        res = self.env.ref(
            'sh_all_in_one_stock_report.sh_non_moving_product_report_action').report_action([], data=datas)
        return res

    def get_xls_report(self):
        ''' Print Xls Report .. '''
        self.ensure_one()
        if self:
            sh_from_date=datetime.combine(self.sh_from_date, datetime.min.time())
            sh_to_date=datetime.combine(self.sh_to_date, datetime.max.time())
            non_move_stock=[]
            # =========== Filter product wise report ==============
            if self.sh_product_ids:
                products=self.sh_product_ids
            else:
                products=self.env['product.product'].search([('detailed_type','=','product')])
                
            # ========= Print report of selected warehouse ============
            if self.sh_selection=='warehouse':
                self._cr.execute('''select id from stock_picking where 
                date_done>=%s and date_done<=%s and location_id IN %s
                and state='done'and picking_type_id IN
                (select id from stock_picking_type where code='outgoing')''',
                [str(sh_from_date),str(sh_to_date),tuple([self.sh_warehouse_id.lot_stock_id.id]+self.sh_warehouse_id.lot_stock_id.child_internal_location_ids.ids)])
                picking_dict = self._cr.dictfetchall()
            
            # ============ Print report of selected Location =============
            elif self.sh_selection=='location':
                if self.sh_location_ids:
                    sh_location_ids=self.sh_location_ids
                else:
                    sh_location_ids=self.env['stock.location'].sudo().search([('usage','=','internal')])
                self._cr.execute('''select id from stock_picking where 
                date_done>=%s and date_done<=%s and location_id IN %s and state='done'and picking_type_id IN
                (select id from stock_picking_type where code='outgoing')''',
                [str(sh_from_date),str(sh_to_date),tuple(sh_location_ids.ids)])
                picking_dict = self._cr.dictfetchall()
                
            # ========== Prepare vals for print report =================    
                
            print(f"==>> picking_dict: {picking_dict}")
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
                            if self.sh_selection=='warehouse':
                                quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.warehouse_id.id == self.sh_warehouse_id.id).mapped('quantity'))
                            elif self.sh_selection=='location':
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
                        if self.sh_selection=='warehouse':
                            quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.warehouse_id.id == self.sh_warehouse_id.id).mapped('quantity'))
                        elif self.sh_selection=='location':
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
                    if self.sh_selection=='warehouse':
                        quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.warehouse_id.id == self.sh_warehouse_id.id).mapped('quantity'))
                    elif self.sh_selection=='location':
                        quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.id in sh_location_ids.ids).mapped('quantity'))      
                    if stock_move:
                        moves = self.env['stock.move'].sudo().browse([r['id'] for r in stock_move])
                        non_move_stock.append([product.display_name,product.default_code,quantity,moves.date.date()])
                    else:
                        non_move_stock.append([product.display_name,product.default_code,quantity,''])
            ############################## XLS REPORT ###################################
            # ============================
            # Get Value
            # ============================
            if non_move_stock:
                
                # ============= Print xls Report =====================
                
                workbook = xlwt.Workbook()
                heading_font_with_background = xlwt.easyxf(
                    'font:height 240,bold True;align: vert center;align: horiz center;pattern: pattern solid,fore_colour gray25;')
                heading_font = xlwt.easyxf(
                    'font:height 210,bold True;align: vert center;align: horiz center;')
                normal_text = xlwt.easyxf(
                    'font:bold False,color black;align: horiz center;align: vert center;')
                worksheet = workbook.add_sheet(
                    'Non Moving Product Report', heading_font_with_background)

                worksheet.col(0).width = 4000
                worksheet.col(1).width = 12000
                worksheet.col(2).width = 5000
                worksheet.col(3).width = 5000
                worksheet.col(4).width = 7000

                worksheet.write_merge(1, 1, 0, 4, 'Non Moving Product Report',heading_font_with_background)

                worksheet.write_merge(3, 3, 0, 0, 'From Date :',heading_font_with_background)
                worksheet.write_merge(4, 4, 0, 0, str(self.sh_from_date),heading_font)
                worksheet.write_merge(3, 3, 1, 1, 'To Date :',heading_font_with_background)
                worksheet.write_merge(4, 4, 1, 1, str(self.sh_to_date),heading_font)
                if self.sh_selection=='warehouse':
                    worksheet.write_merge(3, 3, 2, 4, 'Warehouse',heading_font_with_background)
                    worksheet.write_merge(4, 4, 2, 4, self.sh_warehouse_id.name,heading_font)
                    
                worksheet.write_merge(6, 6, 0, 0, 'Sr No.', heading_font_with_background)
                worksheet.write_merge(6, 6, 1, 1, 'Product Name',heading_font_with_background)
                worksheet.write_merge(6, 6, 2, 2, 'Product Code',heading_font_with_background)
                worksheet.write_merge(6, 6, 3, 3, 'Onhand Qty',heading_font_with_background)
                worksheet.write_merge(6, 6, 4, 4, 'Last Sales',heading_font_with_background)
                

                # Print category wise xls report
                line=7
                for move in non_move_stock:
                    worksheet.write_merge(line, line, 0, 0, line-6, normal_text)
                    worksheet.write_merge(line, line, 1, 1, move[0], normal_text)
                    worksheet.write_merge(line, line, 2, 2, move[1], normal_text)
                    worksheet.write_merge(line, line, 3, 3, move[2], normal_text)
                    worksheet.write_merge(line, line, 4, 4, str(move[3]), normal_text)
                    line+=1

                fp = io.BytesIO()
                workbook.save(fp)
                data = base64.encodebytes(fp.getvalue())
                IrAttachment = self.env['ir.attachment']
                attachment_vals = {
                    "name": "Non_Moving_Product_Report.xls",
                    "res_model": "ir.ui.view",
                    "type": "binary",
                    "datas": data,
                    "public": True,
                }
                fp.close()

                attachment = IrAttachment.search([('name', '=', 'Non_Moving_Product_Report'),
                                                ('type', '=', 'binary'),
                                                ('res_model', '=', 'ir.ui.view')],
                                                limit=1)
                if attachment:
                    attachment.write(attachment_vals)
                else:
                    attachment = IrAttachment.create(attachment_vals)
                # TODO: make user error here
                if not attachment:
                    raise UserError('There is no attachments...')

                url = "/web/content/" + str(attachment.id) + "?download=true"
                return {
                    'type': 'ir.actions.act_url',
                    'url': url,
                    'target': 'new',
                }
            else:
                raise UserError(_('No Records Found..'))

    def sh_non_moving_view(self):
        self.ensure_one()
        if self:
            self._cr.execute(""" DELETE FROM sh_non_moving_product""")
            non_move_stock=[]
            # =========== Filter product wise report ==============
            if self.sh_product_ids:
                products=self.sh_product_ids
            else:
                products=self.env['product.product'].search([('detailed_type','=','product')])
                
            # ========= Print report of selected warehouse ============
            if self.sh_selection=='warehouse':
                self._cr.execute('''select id from stock_picking where 
                date_done>=%s and date_done<=%s and location_id IN %s
                and state='done'and picking_type_id IN
                (select id from stock_picking_type where code='outgoing')''',
                [str(self.sh_from_date),str(self.sh_to_date),tuple([self.sh_warehouse_id.lot_stock_id.id]+self.sh_warehouse_id.lot_stock_id.child_internal_location_ids.ids)])
                picking_dict = self._cr.dictfetchall()
            
            # ============ Print report of selected Location =============
            elif self.sh_selection=='location':
                if self.sh_location_ids:
                    sh_location_ids=self.sh_location_ids
                else:
                    sh_location_ids=self.env['stock.location'].sudo().search([('usage','=','internal')])
                self._cr.execute('''select id from stock_picking where 
                date_done>=%s and date_done<=%s and location_id IN %s and state='done'and picking_type_id IN
                (select id from stock_picking_type where code='outgoing')''',
                [str(self.sh_from_date),str(self.sh_to_date),tuple(sh_location_ids.ids)])
                picking_dict = self._cr.dictfetchall()
                
            # ========== Prepare vals for print report =================    
                
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
                            if self.sh_selection=='warehouse':
                                quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.warehouse_id.id == self.sh_warehouse_id.id).mapped('quantity'))
                            elif self.sh_selection=='location':
                                quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.id in sh_location_ids.ids).mapped('quantity'))      
                            if stock_move:
                                moves = self.env['stock.move'].sudo().browse([r['id'] for r in stock_move])
                                non_move_stock.append([product.id,product.default_code,quantity,moves.date.date(),False])
                            else:
                                non_move_stock.append([product.id,product.default_code,quantity,False,True])
                else:
                    for product in products:
                        self._cr.execute('''select id from stock_move where product_id=(%s) and picking_id in (select id from stock_picking where picking_type_id IN
                        (select id from stock_picking_type where code='outgoing')) and state='done' ORDER BY id DESC LIMIT 1 ''',[product.id])
                        stock_move = self._cr.dictfetchall()
                        if self.sh_selection=='warehouse':
                            quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.warehouse_id.id == self.sh_warehouse_id.id).mapped('quantity'))
                        elif self.sh_selection=='location':
                            quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.id in sh_location_ids.ids).mapped('quantity'))      
                        if stock_move:
                            moves = self.env['stock.move'].sudo().browse([r['id'] for r in stock_move])
                            non_move_stock.append([product.id,product.default_code,quantity,moves.date.date(),False])
                        else:
                            non_move_stock.append([product.id,product.default_code,quantity,False,True])
            else:
                for product in products:
                    self._cr.execute('''select id from stock_move where product_id=(%s) and picking_id in (select id from stock_picking where picking_type_id IN
                    (select id from stock_picking_type where code='outgoing')) and state='done' ORDER BY id DESC LIMIT 1 ''',[product.id])
                    stock_move = self._cr.dictfetchall()
                    if self.sh_selection=='warehouse':
                        quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.warehouse_id.id == self.sh_warehouse_id.id).mapped('quantity'))
                    elif self.sh_selection=='location':
                        quantity=sum(self.env['stock.quant'].search([('product_id','=',product.id)]).filtered(lambda x:x.location_id.id in sh_location_ids.ids).mapped('quantity'))      
                    if stock_move:
                        moves = self.env['stock.move'].sudo().browse([r['id'] for r in stock_move])
                        non_move_stock.append([product.id,product.default_code,quantity,moves.date.date(),False])
                    else:
                        non_move_stock.append([product.id,product.default_code,quantity,False,True])               
            # ============ Create record in view ============= 
            if non_move_stock:
                for non_move in non_move_stock:
                    self.env['sh.non.moving.product'].create({
                        'product_id' : non_move[0],
                        'default_code' : non_move[1],
                        'onhand_qty' : non_move[2],
                        'sh_last_sale' : non_move[3],
                        'sh_no_picking':non_move[4]
                    })                
            return {
                'name': 'Non Moving Product',
                'type': 'ir.actions.act_window',
                'res_model': 'sh.non.moving.product',
                'view_mode': 'tree',
                'view_id': self.env.ref('sh_all_in_one_stock_report.sh_non_moving_product_view_tree').id,
                } 