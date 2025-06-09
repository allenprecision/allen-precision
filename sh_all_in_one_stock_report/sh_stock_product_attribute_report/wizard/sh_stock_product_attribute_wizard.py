# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.


from odoo import api, fields, models,_
import xlwt
from odoo.exceptions import UserError
import base64
import io
from datetime import date
import json


class StockProductAttributeWizard(models.TransientModel):

    _name = "sh.stock.product.attribute.wizard"
    _description = "Stock Product Attribute Wizard"

    sh_from_date = fields.Date(string='From Date', required=True)
    sh_to_date = fields.Date(string='To Date', required=True)
    sh_company_id = fields.Many2one(
        comodel_name='res.company', string='Company', required=True, default=lambda self: self.env.company)
    sh_select_product_cat = fields.Selection([('product', 'Product'), (
        'category', 'Category')], string="Selection Product - Category", default='product')
    sh_category_ids = fields.Many2many(
        comodel_name='product.category', string='Product Category')
    sh_product_ids = fields.Many2many(
        comodel_name='product.product', string='Products')
    sh_vertical_attribute_id = fields.Many2one(
        comodel_name='product.attribute', string='Vertical Attribute', required=True)
    sh_horizontal_attribute_id = fields.Many2one(
        comodel_name='product.attribute', string='Horizontal Attribute', required=True)

    sh_domain = fields.Char(
        string='Domain', compute='_compute_location_domain', store=True)

    @api.depends('sh_company_id')
    def _compute_location_domain(self):
        ''' Compute For add domain in company wise  '''
        for rec in self:
            domain = []
            if rec.sh_company_id:
                domain = [
                    '|', ('company_id', '=', rec.sh_company_id.id), ('company_id', '=', False)]

            rec.sh_domain = json.dumps(domain)

    def sh_print_stock_report(self):
        ''' Print  Qweb Pdf Report'''
        if self.sh_vertical_attribute_id and self.sh_horizontal_attribute_id:
            if self.sh_vertical_attribute_id == self.sh_horizontal_attribute_id:
                raise UserError(
                    'You can not take same attribute in Horizontal attribute and Vertical attribute...')
            else:
                datas = self.read()[0]
                print("\n\n=========datas",datas)
                res = self.env.ref(
                    'sh_all_in_one_stock_report.sh_stock_product_report_action').report_action([], data=datas)
                print("\n\n====res===>",res)
                return res

    def get_xls_report(self):
        ''' Print Xls Report'''
        if self.sh_vertical_attribute_id and self.sh_horizontal_attribute_id:
            if self.sh_vertical_attribute_id == self.sh_horizontal_attribute_id:
                raise UserError(
                    'You can not take same attribute in Horizontal attribute and Vertical attribute...')
            else:
                sh_current_date = date.today()
                sh_stock_move_open = self.env['stock.move'].sudo().search([('date', '>=', self.sh_from_date), (
                    'date', '<=', sh_current_date), '|', ('company_id', '=', self.sh_company_id.id), ('company_id', '=', False)])
                sh_stock_move_close = self.env['stock.move'].sudo().search([('date', '>=', self.sh_from_date), (
                    'date', '<=', self.sh_to_date), '|', ('company_id', '=', self.sh_company_id.id), ('company_id', '=', False)])
                horizontal_attr_list = []
                vertical_attr_list = []
                horizontal_attr_ids_list = self.sh_horizontal_attribute_id.value_ids.ids
                vertical_attr_ids_list = self.sh_vertical_attribute_id.value_ids.ids
                for i in range(0, len(self.sh_horizontal_attribute_id.value_ids.ids)):
                    horizontal_attr_list.append(
                        self.sh_horizontal_attribute_id.value_ids[i].name)
                for j in range(0, len(self.sh_vertical_attribute_id.value_ids.ids)):
                    vertical_attr_list.append(
                        self.sh_vertical_attribute_id.value_ids[j].name)
                category_list = []
                product_list = []

                # Prepare Dict Product wise

                if self.sh_select_product_cat == 'product' and self.sh_product_ids:
                    product_ids = self.sh_product_ids
                else:
                    product_ids = self.env['product.product'].sudo().search([
                        ('id', '>', 0), '|', ('company_id', '=', self.sh_company_id.id), ('company_id', '=', False)])

                # Prepare Dict Category wise

                if self.sh_select_product_cat == 'category' and self.sh_category_ids:
                    category_ids = self.env['product.category'].sudo().search([
                        ('id', 'in', self.sh_category_ids.ids)])
                else:
                    category_ids = self.env['product.category'].sudo().search([
                        ('id', '>', 0)])
                product_attribute_dict = {}

                if product_ids:
                    for product in product_ids:
                        attribute_list = []
                        for x in range(0, len(vertical_attr_ids_list)):
                            attribute_list.append([])
                            for y in range(0, len(horizontal_attr_ids_list)*2):
                                attribute_list[x].append(0)
                        purchase_qty_close = 0
                        sale_qty_close = 0
                        purchase_qty_open = 0
                        sale_qty_open = 0
                        open_stock = 0
                        close_stock = 0
                        x = -1
                        y = -1

                        if self.sh_select_product_cat == 'product' and product_ids:
                            move_lines = self.env['stock.move.line'].sudo().search(
                                [('product_id', '=', product.id), ('move_id', 'in', sh_stock_move_open.ids), '|', ('company_id', '=', self.sh_company_id.id), ('company_id', '=', False)])
                        if self.sh_select_product_cat == 'category' and category_ids:
                            move_lines = self.env['stock.move.line'].sudo().search(
                                [('product_id', '=', product.id), ('move_id', 'in', sh_stock_move_close.ids), '|', ('company_id', '=', self.sh_company_id.id), ('company_id', '=', False)])
                        for order in move_lines:
                            if order.picking_id.picking_type_id.code == "incoming":
                                purchase_qty_open += order.quantity
                            if order.picking_id.picking_type_id.code == "outgoing":
                                sale_qty_open += order.quantity
                            if order.picking_id.picking_type_id.code == "incoming":
                                purchase_qty_close += order.quantity
                            if order.picking_id.picking_type_id.code == "outgoing":
                                sale_qty_close += order.quantity
                        open_stock = product.qty_available-purchase_qty_open+sale_qty_open
                        
                        close_stock = open_stock+purchase_qty_close-sale_qty_close
                        if self.sh_select_product_cat == 'category':
                            if product.categ_id.id in category_ids.ids:
                                if product.categ_id.display_name in product_attribute_dict.keys():
                                    pass
                                else:
                                    category_list.append(
                                        product.categ_id.display_name)
                                    product_attribute_dict[product.categ_id.display_name] = {
                                    }
                        if self.sh_select_product_cat == 'category':
                            if product.categ_id.id in category_ids.ids:
                                if product.name in list(product_attribute_dict[product.categ_id.display_name].keys()):
                                    pass
                                else:
                                    product_attribute_dict[product.categ_id.display_name][product.name] = attribute_list

                        else:
                            if product.name in product_list:
                                pass
                            else:
                                product_attribute_dict[product.name] = attribute_list
                                product_list.append(product.name)
                        if self.sh_select_product_cat == 'category' and product.categ_id.id in category_ids.ids:
                            for att in product.product_template_attribute_value_ids:
                                if att.attribute_id.id == self.sh_horizontal_attribute_id.id:
                                    x = horizontal_attr_list.index(att.name)
                                if att.attribute_id.id == self.sh_vertical_attribute_id.id:
                                    y = vertical_attr_list.index(att.name)
                                if x > -1 and y > -1 and open_stock and close_stock:
                                    product_attribute_dict[product.categ_id.display_name][product.name][y][(
                                        x*2)] += open_stock
                                    product_attribute_dict[product.categ_id.display_name][product.name][y][(
                                        x*2)+1] += close_stock
                        if self.sh_select_product_cat == 'product':
                            for att in product.product_template_attribute_value_ids:
                                if att.attribute_id.id == self.sh_horizontal_attribute_id.id:
                                    x = horizontal_attr_list.index(att.name)
                                if att.attribute_id.id == self.sh_vertical_attribute_id.id:
                                    y = vertical_attr_list.index(att.name)
                                if x > -1 and y > -1 and open_stock and close_stock:
                                    product_attribute_dict[product.name][y][(
                                        x*2)] = open_stock
                                    product_attribute_dict[product.name][y][(
                                        x*2)+1] = close_stock

                # Print Xls Report

                workbook = xlwt.Workbook()
                normal_record = xlwt.easyxf(
                    'font:height 210;align: vert center')
                heading_format = xlwt.easyxf(
                    'font:height 245,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
                worksheet = workbook.add_sheet(
                    "stock Product Report", heading_format)

                worksheet.col(0).width = 8000
                worksheet.col(1).width = 5000
                worksheet.col(2).width = 5000
                worksheet.col(3).width = 5000
                worksheet.col(4).width = 5000
                worksheet.col(5).width = 5000
                worksheet.col(6).width = 5000
                worksheet.col(7).width = 5000

                line_var = 1
                worksheet.write_merge(line_var, line_var, 1, 4,
                                      'Stock Product Report', heading_format)
                line_var += 2
                worksheet.write_merge(
                    line_var, line_var, 1, 2, 'From Date : ' + str(self.sh_from_date), heading_format)
                worksheet.write_merge(
                    line_var, line_var, 3, 4, 'To Date : ' + str(self.sh_to_date), heading_format)
                line_var += 2
                if product_attribute_dict:

                    # Print xls report Catgeory wise

                    if self.sh_select_product_cat == 'category':
                        line_var += 1
                        for cat in range(0, len(product_attribute_dict)):
                            worksheet.write_merge(
                                line_var, line_var, 1, 1, 'Category : ', heading_format)
                            cat1 = list(
                                product_attribute_dict.keys())
                            worksheet.write_merge(
                                line_var, line_var, 2, 3, cat1[cat], heading_format)
                            line_var += 2

                            worksheet.write_merge(
                                line_var, line_var+1, 0, 0, 'Product', heading_format)
                            worksheet.write_merge(
                                line_var, line_var+1, 1, 1, 'Attribute', heading_format)
                            temp_line = line_var
                            v_line = 2
                            for h in range(0, len(horizontal_attr_list)):
                                worksheet.write_merge(
                                    temp_line, temp_line, v_line, v_line+1, horizontal_attr_list[h], heading_format)
                                worksheet.write_merge(
                                    temp_line+1, temp_line+1, v_line, v_line, 'Open Stock', heading_format)
                                worksheet.write_merge(
                                    temp_line+1, temp_line+1, v_line+1, v_line+1, 'Close Stock', heading_format)
                                v_line += 2
                            count = 1
                            line_var += 1
                            product_list = list(
                                product_attribute_dict[cat1[cat]].keys())
                            for rec in range(0, len(product_list)):
                                worksheet.write_merge(
                                    line_var+1, line_var+1, 0, 0, product_list[rec], normal_record)
                                for x in range(0, len(vertical_attr_list)):
                                    worksheet.write_merge(
                                        line_var+count, line_var+count, 1, 1, vertical_attr_list[x], normal_record)
                                    for y in range(0, len(horizontal_attr_list)*2, 2):
                                        worksheet.write_merge(
                                            line_var+count, line_var+count, y+2, y+2, product_attribute_dict[cat1[cat]][product_list[rec]][x][y], normal_record)
                                        worksheet.write_merge(
                                            line_var+count, line_var+count, y+3, y+3, product_attribute_dict[cat1[cat]][product_list[rec]][x][y+1], normal_record)

                                    line_var += 1
                                line_var += 1
                            line_var += 1

                    # Print xls report Product wise

                    if self.sh_select_product_cat == 'product':
                        worksheet.write_merge(
                            line_var, line_var+1, 0, 0, 'Product', heading_format)
                        worksheet.write_merge(
                            line_var, line_var+1, 1, 1, 'Attribute', heading_format)
                        temp_line = line_var
                        v_line = 2
                        for h in range(0, len(horizontal_attr_list)):
                            worksheet.write_merge(
                                temp_line, temp_line, v_line, v_line+1, horizontal_attr_list[h], heading_format)
                            worksheet.write_merge(
                                temp_line+1, temp_line+1, v_line, v_line, 'Open Stock', heading_format)
                            worksheet.write_merge(
                                temp_line+1, temp_line+1, v_line+1, v_line+1, 'Close Stock', heading_format)
                            v_line += 2
                        line_var += 1
                        count = 1
                        product_list = list(product_attribute_dict.keys())
                        for rec in range(0, len(product_list)):
                            worksheet.write_merge(
                                line_var+1, line_var+1, 0, 0, product_list[rec], normal_record)
                            for x in range(0, len(vertical_attr_list)):
                                worksheet.write_merge(
                                    line_var+count, line_var+count, 1, 1, vertical_attr_list[x], normal_record)
                                for y in range(0, len(horizontal_attr_list)*2, 2):
                                    worksheet.write_merge(
                                        line_var+count, line_var+count, y+2, y+2, product_attribute_dict[product_list[rec]][x][y], normal_record)
                                    worksheet.write_merge(
                                        line_var+count, line_var+count, y+3, y+3, product_attribute_dict[product_list[rec]][x][y+1], normal_record)
                                line_var += 1
                            line_var += 1
                        line_var += 1
                else:
                    raise UserError(_('There is no data in between these dates.....'))

                fp = io.BytesIO()
                workbook.save(fp)
                data = base64.encodebytes(fp.getvalue())
                IrAttachment = self.env['ir.attachment']
                attachment_vals = {
                    "name": "stock product.xls",
                    "res_model": "ir.ui.view",
                    "type": "binary",
                    "datas": data,
                    "public": True,
                }
                fp.close()

                attachment = IrAttachment.search([('name', '=', 'stock_product'),
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
