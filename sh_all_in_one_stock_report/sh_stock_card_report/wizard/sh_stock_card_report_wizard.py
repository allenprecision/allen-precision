# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api,_
import xlwt
from odoo.exceptions import UserError
import base64
import io
from datetime import date,datetime,timedelta
import json
import pytz


class StockCardReportWizard(models.TransientModel):
    _name = 'sh.stock.card.report.wizard'
    _description = 'Stock Card Report Wizard'

    sh_from_date = fields.Date(string='From Date', required=True)
    sh_to_date = fields.Date(string='To Date', required=True)
    sh_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string='Warehouse', required=True)
    sh_location_id = fields.Many2one(
        comodel_name='stock.location', string='Location', required=True)
    sh_company_id = fields.Many2one(
        comodel_name='res.company', string='Company', required=True)
    sh_select_product_cat = fields.Selection([('product', 'Product'), (
        'category', 'Category')], string="Group BY Product - Category", default='product', required=True)
    sh_product_ids = fields.Many2many(
        comodel_name='product.product', string='Product', domain=[('detailed_type', '=', 'product')])
    sh_category_ids = fields.Many2many(
        comodel_name='product.category', string='Category')
    sh_domain = fields.Char(
        string='Domain', compute='_compute_location_domain', store=True)
    sh_domain_warehouse = fields.Char(
        string='Domain warehouse', compute='_compute_location_domain', store=True)

    @api.depends('sh_warehouse_id', 'sh_company_id')
    def _compute_location_domain(self):
        for rec in self:
            domain = [('id', '<', 0)]
            sh_domain_ware = [('id', '<', 0)]
            ''' Compute For add domain in, location(Warehouse-wise)  '''
            if rec.sh_company_id:
                sh_domain_ware = [
                    ('company_id', '=', self.sh_company_id.id)]
            if rec.sh_warehouse_id:
                inventory_loss_location = self.env['stock.location'].sudo().search(
                    [('usage', '=', 'inventory'), ('company_id', '=', self.sh_company_id.id)])
                location_ids = self.env['stock.location'].sudo().search([]).sudo().filtered(
                    lambda x: x.warehouse_id.id == rec.sh_warehouse_id.id)
                if location_ids:
                    domain = [('id', 'in',  location_ids.ids +
                               inventory_loss_location.ids)]
            rec.sh_domain = json.dumps(domain)
            rec.sh_domain_warehouse = json.dumps(sh_domain_ware)

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
            'sh_all_in_one_stock_report.sh_stock_card_report_action').report_action([], data=datas)
        return res

    def get_xls_report(self):
        self.ensure_one()
        user = self.env.user
        stock_card_dict = {}
        # Prepare dictionary category wise
        sh_current_date = date.today()
        sh_current_date = datetime.combine(sh_current_date, datetime.min.time())+timedelta(days=1)
        sh_from_datetime=datetime.combine(self.sh_from_date, datetime.min.time())
        sh_to_datetime=datetime.combine(self.sh_to_date, datetime.min.time())+timedelta(days=1)
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        today = user_tz.localize(fields.Datetime.from_string(str(sh_from_datetime)))
        sh_from_datetime = today.astimezone(pytz.timezone('UTC'))
        sh_from_datetime = datetime.strptime(str(sh_from_datetime)[:19], "%Y-%m-%d %H:%M:%S")
        today = user_tz.localize(fields.Datetime.from_string(str(sh_to_datetime)))
        sh_to_datetime = today.astimezone(pytz.timezone('UTC'))
        sh_to_datetime = datetime.strptime(str(sh_to_datetime)[:19], "%Y-%m-%d %H:%M:%S")
        today = user_tz.localize(fields.Datetime.from_string(str(sh_current_date)))
        sh_current_date = today.astimezone(pytz.timezone('UTC'))
        if self.sh_select_product_cat == 'category':
            category_list = []
            product_dict = {}
            if self.sh_category_ids:
                sh_category = self.env['product.category'].sudo().search(
                    [('id', 'in', self.sh_category_ids.ids)])
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
                                [product.id,str(sh_from_datetime),str(sh_current_date)])
                            pos_r_qty_open = self._cr.dictfetchall()
                            pos_r_qty_open=sum([sub['qty'] for sub in pos_r_qty_open ])
                        
                            self._cr.execute('''select id,qty,order_id from pos_order_line where product_id = %s and qty<0 and order_id IN 
                                (select id from pos_order where date_order>= %s and date_order<= %s and state IN ('paid','done','invoiced'))''',
                                [product.id,str(sh_from_datetime),str(sh_current_date)])
                            pos_return_order = self._cr.dictfetchall()
                            pos_return_picking= self.env['pos.order'].sudo().browse([r['order_id'] for r in pos_return_order]).mapped('picking_ids').mapped('id')
                        
                        sale_order_domain_open = [
                            ('product_id', '=', product.id),
                            ('date', '>=', sh_from_datetime),
                            ('date', '<=', sh_current_date),
                            ('state', '=', 'done'),
                            ('company_id', '=', self.sh_company_id.id),
                            ('picking_id','not in',pos_return_picking),
                            '|',
                            ('location_id', '=', self.sh_location_id.id),
                            ('location_dest_id', '=', self.sh_location_id.id)
                        ]
                        sale_stock_order_open = self.env['stock.move.line'].sudo().search(
                            sale_order_domain_open)
                        product_onhand = self.env['stock.quant'].sudo().search(
                            [('location_id', '=', self.sh_location_id.id), ('product_id', '=', product.id)], limit=1)
                        if product_onhand:
                            onhand = product_onhand.quantity
                        if sale_stock_order_open:
                            for order in sale_stock_order_open:
                                if order.location_id.id != order.location_dest_id.id :
                                    if order.product_uom_id.id != order.product_id.uom_id.id:
                                        qty_done = order.product_uom_id.sh_compute_quantity(order.quantity, order.product_id.uom_id)
                                    else:
                                        qty_done = order.quantity
                                    if order.location_id.id == self.sh_location_id.id:
                                        transfer += qty_done
                                    elif order.location_dest_id.id == self.sh_location_id.id:
                                        transfer -= qty_done
                        open_stock = onhand+transfer+pos_r_qty_open

                        # Display Movement of Product in Stock (Sale , Purhcase , Internal Transfer , Adjustment , Scrap)

                        stock_move = self.env['stock.move.line'].sudo().search(
                            [('product_id', '=', product.id), ('date', '>=', sh_from_datetime), 
                             ('date', '<=', self.sh_to_date), ('state', '=', 'done'), 
                             ('company_id', '=', self.sh_company_id.id), 
                             '|', ('location_id', '=', self.sh_location_id.id), 
                             ('location_dest_id', '=', self.sh_location_id.id)], order='date asc')
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
                                    
                                    if move.location_id.id == self.sh_location_id.id:
                                        total_out_qty += move.quantity
                                        out_qty = move.quantity
                                    elif move.location_dest_id.id == self.sh_location_id.id:
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
                        if total_in_qty or total_out_qty or close_stock or lines_list:
                            product_dict[category.display_name].append(
                                product.display_name)
                            stock_card_dict[category.display_name][product.display_name] = {
                                'open_stock': open_stock, 'lines': lines_list, 'total': ['', '', total_in_qty, total_out_qty, close_stock]}
                if len(product_dict[category.display_name]) > 0:
                    category_list.append(category.display_name)
                if not stock_card_dict[category.display_name]:
                    del stock_card_dict[category.display_name]

        # Prepare dictionary Product wise

        elif self.sh_select_product_cat == 'product':
            product_list = []
            if self.sh_product_ids:
                sh_products = self.env['product.product'].sudo().search(
                    [('id', 'in', self.sh_product_ids.ids)])
            else:
                sh_products_get = self.env['stock.quant'].sudo().search(
                    [('location_id', '=', self.sh_location_id.id)])
                sh_products_get = sh_products_get.mapped('product_id')
                sh_products = self.env['product.product'].sudo().search(
                    [('id', 'in', sh_products_get.ids), ('detailed_type', '=', 'product'), '|', ('company_id', '=', self.sh_company_id.id), ('company_id', '=', False)])
            if sh_products:
                for product in sh_products:
                    move_date = False
                    origin = False                    
                    lines_list = []
                    total_out_qty = 0.0
                    total_in_qty = 0.0
                    close_stock = 0.0
                    transfer = 0.0
                    onhand = 0.0
                    # Calculate Opeing Balance

                    pos_return_picking=[]
                    pos_r_qty_open=0
                    # ================================================
                    # CHECK POS MODULE IS INSTALLED OR NOT  
                    # ================================================
                    is_pos_installed = self.env['ir.module.module'].sudo().search(
                        [('name', '=', 'point_of_sale'),('state','=','installed')], limit=1)
                    if is_pos_installed:
                        # ================================================
                        # Calculate pos return qty 
                        # ================================================
                        self._cr.execute('''select id,qty from pos_order_line where product_id = %s and qty<0 and order_id IN (select id from pos_order where date_order>= %s and date_order<= %s and state IN ('paid','done','invoiced'))''',
                            [product.id,str(sh_from_datetime),str(sh_current_date)])
                        pos_r_qty_open = self._cr.dictfetchall()
                        pos_r_qty_open=sum([sub['qty'] for sub in pos_r_qty_open ])
                    
                        self._cr.execute('''select id,qty,order_id from pos_order_line where product_id = %s and qty<0 and order_id IN 
                            (select id from pos_order where date_order>= %s and date_order<= %s and state IN ('paid','done','invoiced'))''',
                            [product.id,str(sh_from_datetime),str(sh_current_date)])
                        pos_return_order = self._cr.dictfetchall()
                        pos_return_picking= self.env['pos.order'].sudo().browse([r['order_id'] for r in pos_return_order]).mapped('picking_ids').mapped('id')
                    
                    sale_order_domain_open = [
                        ('product_id', '=', product.id),
                        ('date', '>=', sh_from_datetime),
                        ('date', '<=', sh_current_date),
                        ('state', '=', 'done'),
                        ('company_id', '=', self.sh_company_id.id),
                        ('picking_id','not in',pos_return_picking),
                        '|',
                        ('location_id', '=', self.sh_location_id.id),
                        ('location_dest_id', '=', self.sh_location_id.id)
                    ]
                    sale_stock_order_open = self.env['stock.move.line'].sudo().search(
                        sale_order_domain_open)
                    product_onhand = self.env['stock.quant'].sudo().search(
                        [('location_id', '=', self.sh_location_id.id), ('product_id', '=', product.id)], limit=1)
                    if product_onhand:
                        onhand = product_onhand.quantity
                    if sale_stock_order_open:
                        for order in sale_stock_order_open:
                            if order.location_id.id != order.location_dest_id.id :
                                if order.product_uom_id.id != order.product_id.uom_id.id:
                                    qty_done = order.product_uom_id.sh_compute_quantity(order.quantity, order.product_id.uom_id)
                                else:
                                    qty_done = order.quantity
                                if order.location_id.id == self.sh_location_id.id:
                                    transfer += qty_done
                                elif order.location_dest_id.id == self.sh_location_id.id:
                                    transfer -= qty_done
                    open_stock = onhand+transfer+pos_r_qty_open
                     
                    # Display Movement of Product in Stock (Sale , Purhcase , Internal Transfer , Adjustment , Scrap)

                    stock_move = self.env['stock.move.line'].sudo().search(
                        [('product_id', '=', product.id),
                         ('date', '>=', sh_from_datetime),
                         ('date', '<=', self.sh_to_date),
                         ('state', '=', 'done'),
                         ('company_id', '=', self.sh_company_id.id),
                         '|',
                         ('location_id', '=', self.sh_location_id.id),
                         ('location_dest_id', '=', self.sh_location_id.id)
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
                                if move.location_id.id == self.sh_location_id.id:
                                    total_out_qty += move.quantity
                                    out_qty = move.quantity
                                elif move.location_dest_id.id == self.sh_location_id.id:
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
                            '', '', total_in_qty, total_out_qty, close_stock]}
        
        
        ############################## XLS REPORT ###################################
        # ============================
        # Get Value
        # ============================

        workbook = xlwt.Workbook()
        heading_font_with_background = xlwt.easyxf(
            'font:height 240,bold True;align: vert center;align: horiz center;pattern: pattern solid,fore_colour gray25;')
        heading_font = xlwt.easyxf(
            'font:height 210,bold True;align: vert center;align: horiz center;')
        product_font = xlwt.easyxf(
            'font:bold True,color black;align: horiz center;align: vert center;pattern:pattern solid,fore_colour tan;')
        category_font = xlwt.easyxf(
            'font:height 220,bold True,color black;align: horiz center;align: vert center;pattern:pattern solid,fore_colour aqua;')
        normal_text = xlwt.easyxf(
            'font:bold False,color black;align: horiz center;align: vert center;')
        bold_text = xlwt.easyxf(
            'font:bold True,color black;align: horiz center;align: vert center;')
        worksheet = workbook.add_sheet(
            'STOCK CARD REPORT', heading_font_with_background)

        worksheet.col(0).width = 5000
        worksheet.col(1).width = 10000
        worksheet.col(2).width = 5000
        worksheet.col(3).width = 5000
        worksheet.col(4).width = 5000
        worksheet.col(5).width = 5000
        worksheet.col(6).width = 6000
        worksheet.col(7).width = 6000
        worksheet.write_merge(1, 1, 0, 4, 'STOCK CARD REPORT',
                              heading_font_with_background)
        worksheet.write_merge(
            3, 3, 0, 0, 'Warehouse',
            heading_font_with_background)
        worksheet.write_merge(
            3, 3, 1, 1, 'Location',
            heading_font_with_background)
        worksheet.write_merge(
            3, 3, 2, 3, 'Date',
            heading_font_with_background)
        worksheet.write_merge(
            3, 3, 4, 4, 'Generated BY ',
            heading_font_with_background)
        worksheet.write_merge(
            4, 4, 0, 0, self.sh_warehouse_id.name,
            heading_font)
        worksheet.write_merge(
            4, 4, 1, 1, self.sh_location_id.complete_name,
            heading_font)
        worksheet.write_merge(
            4, 4, 2, 3, str(self.sh_from_date)+" To "+str(self.sh_to_date),
            heading_font)
        worksheet.write_merge(
            4, 4, 4, 4, user.name,
            heading_font)

        worksheet.write_merge(6, 6, 0, 0, 'Date', heading_font_with_background)
        worksheet.write_merge(6, 6, 1, 1, 'Origin',
                              heading_font_with_background)
        worksheet.write_merge(6, 6, 2, 2, 'In Quantity',
                              heading_font_with_background)
        worksheet.write_merge(6, 6, 3, 3, 'Out Quantity',
                              heading_font_with_background)
        worksheet.write_merge(6, 6, 4, 4, 'Balance',
                              heading_font_with_background)

        # Print category wise xls report
        if stock_card_dict:
            if self.sh_select_product_cat == 'category':
                line_var = 8
                for category in category_list:
                    worksheet.write_merge(
                        line_var, line_var, 0, 4, category, category_font)
                    line_var += 2
                    for product in product_dict[category]:
                        worksheet.write_merge(
                            line_var, line_var, 0, 4, product, product_font)
                        line_var += 1
                        worksheet.write_merge(
                            line_var, line_var, 0, 3, 'Opening Balance', bold_text)
                        worksheet.write_merge(
                            line_var, line_var, 4, 4, stock_card_dict[category][product]['open_stock'], bold_text)
                        line_var += 1
                        for line in stock_card_dict[category][product]['lines']:
                            worksheet.write_merge(
                                line_var, line_var, 0, 0, str(line[0]), normal_text)
                            worksheet.write_merge(
                                line_var, line_var, 1, 1, line[1], normal_text)
                            worksheet.write_merge(
                                line_var, line_var, 2, 2, line[2], normal_text)
                            worksheet.write_merge(
                                line_var, line_var, 3, 3, line[3], normal_text)
                            worksheet.write_merge(
                                line_var, line_var, 4, 4, line[4], normal_text)
                            line_var += 1
                        worksheet.write_merge(
                            line_var, line_var, 1, 1, 'TOTAL', bold_text)
                        worksheet.write_merge(
                            line_var, line_var, 2, 2, stock_card_dict[category][product]['total'][2], bold_text)
                        worksheet.write_merge(
                            line_var, line_var, 3, 3, stock_card_dict[category][product]['total'][3], bold_text)
                        worksheet.write_merge(
                            line_var, line_var, 4, 4, stock_card_dict[category][product]['total'][4], bold_text)
                        line_var += 2

            # Print Product wise xls report

            elif self.sh_select_product_cat == 'product' and product_list:
                line_var = 7
                for product in product_list:
                    worksheet.write_merge(
                        line_var, line_var, 0, 4, product, product_font)
                    line_var += 1
                    worksheet.write_merge(
                        line_var, line_var, 0, 3, 'Opening Balance', bold_text)
                    worksheet.write_merge(
                        line_var, line_var, 4, 4, stock_card_dict[product]['open_stock'], bold_text)
                    line_var += 1
                    for line in stock_card_dict[product]['lines']:
                        worksheet.write_merge(
                            line_var, line_var, 0, 0, str(line[0]), normal_text)
                        worksheet.write_merge(
                            line_var, line_var, 1, 1, line[1], normal_text)
                        worksheet.write_merge(
                            line_var, line_var, 2, 2, line[2], normal_text)
                        worksheet.write_merge(
                            line_var, line_var, 3, 3, line[3], normal_text)
                        worksheet.write_merge(
                            line_var, line_var, 4, 4, line[4], normal_text)
                        line_var += 1
                    worksheet.write_merge(
                        line_var, line_var, 1, 1, 'TOTAL', bold_text)
                    worksheet.write_merge(
                        line_var, line_var, 2, 2, stock_card_dict[product]['total'][2], bold_text)
                    worksheet.write_merge(
                        line_var, line_var, 3, 3, stock_card_dict[product]['total'][3], bold_text)
                    worksheet.write_merge(
                        line_var, line_var, 4, 4, stock_card_dict[product]['total'][4], bold_text)
                    line_var += 2
        else:
            raise UserError(_('No Data Found .....'))

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "STOCK_CARD_REPORT.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'STOCK_CARD_REPORT'),
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
