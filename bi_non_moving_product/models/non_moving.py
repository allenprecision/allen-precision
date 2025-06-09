# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import base64
from io import StringIO
from odoo import api, fields, models
import io
from dateutil.relativedelta import relativedelta

try:
    import xlwt
except ImportError:
    xlwt = None

class NonMovingProductWizard(models.Model):
    _name = "non.moving.product.wizard"
    _description="NonMovingProductWizard"
    
    start_date = fields.Datetime('Start Period', required=True)
    end_date = fields.Datetime('End Period', required=True)
    warehouse = fields.Many2many('stock.warehouse', 'wh_wiz_rel_non_mov', 'wh', 'wiz', string='Warehouse',required=True)
    

    def get_warehouse(self):
        if self.warehouse:
            l1 = []
            l2 = []
            for i in self.warehouse:
                obj = self.env['stock.warehouse'].search([('id', '=', i.id)])
                for j in obj:
                    l2.append(j.id)
            return l2
        return []
    
    def _get_warehouse_name(self):
        if self.warehouse:
            l1 = []
            l2 = []
            for i in self.warehouse:
                obj = self.env['stock.warehouse'].search([('id', '=', i.id)])
                l1.append(obj.name)
                myString = ",".join(l1 )
            return myString
        return ''

    def get_lines(self, warehouse):
        product_list=[]
        lines = []
        get_warehouse = self.get_warehouse()
        sale_obj = self.env['sale.order.line']
        product_obj = self.env['product.product']
        all_product_id = self.env['product.product'].search([])
        all_list = []
        for pro in all_product_id:
            all_list.append(pro.id) 
        product_ids = []
        final_list = []
        final_list_pro = []
        sale_order_line_list = []
        sale_ids = sale_obj.search([('order_id.state','in',['sale','done']),('create_date','>=', self.start_date),('create_date','<=', self.end_date)])
        
        for line in sale_ids:
            product_ids.append(line.product_id.id)

        for pro in all_list:
            if product_ids.count(pro) == 0:
               final_list_pro.append(pro)
            else:
                continue 
        for pro in  final_list_pro:

            self._cr.execute("""select max(id) from sale_order_line where product_id ='%s';""",(pro,))
            uniq_dates_records = self._cr.dictfetchall()
            if uniq_dates_records[0].get('max') != None:
               sale_order_line_list.append(uniq_dates_records[0].get('max'))

        for line in sale_order_line_list:
                
                sale_order_line_obj = self.env['sale.order.line'].browse(line)
                
                if sale_order_line_obj.product_id.qty_available > 0:
                    finish_dt = fields.Datetime.from_string(self.end_date)
                    start_dt = fields.Datetime.from_string(sale_order_line_obj.create_date)
                    difference = relativedelta(finish_dt,start_dt )
                    days = difference.days
                    a=finish_dt -start_dt
                   
                    vals ={
                        'id':sale_order_line_obj.product_id.id,
                        'name':sale_order_line_obj.product_id.name,
                        'qty_available':sale_order_line_obj.product_id.qty_available,
                        'code':sale_order_line_obj.product_id.default_code,
                        'last_sale':sale_order_line_obj.create_date,
                        'duration':a.days,
                      }

                    lines.append(vals)

 
        return lines

    def print_exl_report(self):
        filename = 'Non Moving Products Report.xls'
        get_warehouse = self.get_warehouse()
        get_warehouse_name = self._get_warehouse_name()
        l1 = []
        workbook = xlwt.Workbook()
        stylePC = xlwt.XFStyle()
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER
        fontP = xlwt.Font()

        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        fontP.bold = True
        fontP.height = 200
        stylePC.font = fontP
        stylePC.num_format_str = '@'
        stylePC.alignment = alignment
        style_title = xlwt.easyxf("font:height 300; font: name Liberation Sans, bold on,color black; align: horiz center")
        style_table_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center")
        style = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black;")
        worksheet = workbook.add_sheet('Sheet 1')
        worksheet.write_merge(3, 3, 1, 2,'Start Date:', style_table_header)
        worksheet.write_merge(4, 4, 1, 2,self.start_date, date_format)
        worksheet.write_merge(3, 3, 3, 4,'End Date', style_table_header)
        worksheet.write_merge(4, 4, 3, 4,self.end_date, date_format)
        worksheet.write_merge(3, 3, 5, 6,'Warehouse(s)', style_table_header)
        w_col_no = 7
        w_col_no1 = 8
        if get_warehouse_name:
            worksheet.write_merge(4, 4, 5, 6,get_warehouse_name, stylePC)
        worksheet.write_merge(0, 1, 1, 5, "Non Moving Products Report", style=style_title)
        worksheet.write_merge(6, 6, 0, 1, 'Product ID', style_table_header)
        worksheet.write_merge(6, 6, 2, 3, 'Default Code', style_table_header)
        worksheet.write_merge(6, 6, 4, 5, 'Product Name', style_table_header)
        worksheet.write_merge(6, 6, 6, 7, 'Available Qty', style_table_header)
        worksheet.write(6, 8, 'Last Sale Time', style_table_header)
        worksheet.write_merge(6, 6, 9, 10,'Duration From Last Sale In Days', style_table_header)
        prod_row = 7
        prod_col = 0
        for i in get_warehouse:
           
            get_line = self.get_lines(i)
            
            for each in get_line:
                
                worksheet.write_merge(prod_row, prod_row,prod_col, prod_col+1,each['id'], style)
                worksheet.write_merge(prod_row, prod_row,prod_col+2,prod_col+3, each['code'], style)
                worksheet.write_merge(prod_row, prod_row,prod_col+4, prod_col+5,each['name'], style)
                worksheet.write_merge(prod_row, prod_row,prod_col+6, prod_col+7,each['qty_available'], style)
                if each['last_sale']:
                    worksheet.write(prod_row,prod_col+8,each['last_sale'] or '', date_format)
                if each['duration']:
                    worksheet.write_merge(prod_row,prod_row,prod_col+9,prod_col+10,each['duration'] or '', style)
                prod_row = prod_row + 1
            break
        prod_row = 6
        prod_col = 7
        fp = io.BytesIO()
        workbook.save(fp)
        
        export_id = self.env['non.moving.report.excel'].create({'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': filename})
        res = {
                        'view_mode': 'form',
                        'res_id': export_id.id,
                        'res_model': 'non.moving.report.excel',
                        'view_type': 'form',
                        'type': 'ir.actions.act_window',
                        'target':'new'
                }
        return res



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
