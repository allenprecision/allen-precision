#!/usr/bin/python
# -*- coding: utf-8 -*-

# Part of Softhealer Technologies.

from odoo import models, fields , _
import xlwt
from odoo.exceptions import UserError
import base64
import io
import pytz


class XYZStockValuationWizard(models.TransientModel):

    _name = 'sh.xyz.stock.valuation.wizard'
    _description = 'XYZ Stock Valuation Wizard'

    sh_date = fields.Datetime(string='Date', required=True)

    def sh_print_stock_report(self):
        datas = self.read()[0]
        res = \
            self.env.ref('sh_all_in_one_stock_report.sh_xyz_stock_report_action'
                         ).report_action([], data=datas)
        return res

    def get_xls_report(self):
        if self and self.sh_date:
            stock_valuation_records = self.env['stock.valuation.layer'].sudo().search([])
            product_ids_in_valuation = stock_valuation_records.mapped('product_id.id')
            sh_products = self.env['product.product'].sudo().search([('id', 'in', product_ids_in_valuation)])
            # sh_products = self.env['product.product'
            #                        ].sudo().search([('id', '>', 0)])
            timezone = pytz.timezone(self.env.user.tz or 'UTC')
            sh_date = \
                pytz.utc.localize(self.sh_date).astimezone(timezone)
            sh_print_date = str(sh_date).split('+')[0]
            stock_valuation_list = []
            if sh_products:
                for product in sh_products:

                    # sh_date = datetime.combine(
                    #     self.sh_date, datetime.max.time())

                    total_value = 0
                    sh_stock_valuation = \
                        self.env['stock.valuation.layer'
                                 ].sudo().search([('product_id', '=',
                            product.id)])
                    # ================================================
                    # get stock valuation value
                    # ================================================

                    for stock_id in sh_stock_valuation:
                        sh_create_date = \
                            pytz.utc.localize(stock_id.create_date).astimezone(timezone)
                        if sh_create_date <= sh_date:
                            total_value += round(stock_id.quantity, 2)
                    product_stock_valuation = [product.display_name,
                            total_value, 0, 0, 0]
                    stock_valuation_list.append(product_stock_valuation)

                # ================================================
                # sort list descending order
                # ================================================

                stock_valuation_list.sort(key=lambda e: e[1],
                        reverse=True)

                # stock_valuation_list.sort(reverse=True)

                all_pro_total = 0

                # ================================================
                # get total valuation of all product
                # ================================================

                for stock_val in stock_valuation_list:
                    all_pro_total += round(stock_val[1], 2)

                # ================================================
                # find value in % of total valuation
                # ================================================
                if all_pro_total > 0:
                    for stock_val in stock_valuation_list:
                        stock_val[2] = round(100 * stock_val[1]
                                / all_pro_total, 2)

                    # ================================================
                    # Calculate Cummulative of total valuation
                    # ================================================

                    for index in range(0, len(stock_valuation_list)):

                        if stock_valuation_list[index - 1]:
                            stock_valuation_list[index][3] = \
                                round(stock_valuation_list[index
                                    - 1][3]
                                    + stock_valuation_list[index][2], 2)
                        else:
                            stock_valuation_list[index][3] = \
                                round(stock_valuation_list[index][2], 2)

                    # ================================================
                    # Calculate Cummulative of total valuation
                    # ================================================

                    for index in range(0, len(stock_valuation_list)):

                        if stock_valuation_list[index][3] > 0 \
                            and stock_valuation_list[index][3] < 70:
                            stock_valuation_list[index][4] = 'X'
                        elif stock_valuation_list[index][3] >= 70 \
                            and stock_valuation_list[index][3] < 90:
                            stock_valuation_list[index][4] = 'Y'
                        elif stock_valuation_list[index][3] >= 90 \
                            and stock_valuation_list[index][3] <= 100:
                            stock_valuation_list[index][4] = 'Z'
                else:
                    raise UserError(_('No Data Found .....'))            
                if stock_valuation_list:

                    # ############################ XLS REPORT ###################################
                    # ============================
                    # Get Value
                    # ============================

                    workbook = xlwt.Workbook()
                    bold_center = \
                        xlwt.easyxf('font:height 250,bold True;align: vert center;align: horiz center;pattern: pattern solid,fore_colour gray25;'
                                    )
                    orange_text = \
                        xlwt.easyxf('font:bold True,color orange;align: horiz center;align: vert center'
                                    )
                    green_text = \
                        xlwt.easyxf('font:bold True,color green;align: horiz center;align: vert center'
                                    )
                    gray_text = \
                        xlwt.easyxf('font:bold True,color gray50;align: horiz center;align: vert center'
                                    )
                    worksheet = \
                        workbook.add_sheet('XYZ Stock Valuation Report'
                            , bold_center)

                    worksheet.col(0).width = 1500
                    worksheet.col(1).width = 15000
                    worksheet.col(2).width = 6000
                    worksheet.col(3).width = 7000
                    worksheet.col(4).width = 5000
                    worksheet.col(5).width = 5000
                    worksheet.write_merge(
                        1,
                        1,
                        1,
                        3,
                        'XYZ Stock Valuation Report',
                        bold_center,
                        )
                    worksheet.write_merge(
                        3,
                        3,
                        1,
                        3,
                        'Date : ' + str(sh_print_date),
                        bold_center,
                        )

                    worksheet.write_merge(
                        6,
                        6,
                        0,
                        0,
                        'No.',
                        bold_center,
                        )
                    worksheet.write_merge(
                        6,
                        6,
                        1,
                        1,
                        'Product',
                        bold_center,
                        )
                    worksheet.write_merge(
                        6,
                        6,
                        2,
                        2,
                        'Stock Valuation',
                        bold_center,
                        )
                    worksheet.write_merge(
                        6,
                        6,
                        3,
                        3,
                        'Stock Valuation(%)',
                        bold_center,
                        )
                    worksheet.write_merge(
                        6,
                        6,
                        4,
                        4,
                        'Cummulative',
                        bold_center,
                        )
                    worksheet.write_merge(
                        6,
                        6,
                        5,
                        5,
                        'XYZ Analysis',
                        bold_center,
                        )

                    # if stock_valuation_list:
                    count_var = 1
                    line_var = 7
                    for index in range(0,
                            len(stock_valuation_list)):
                        if stock_valuation_list[index][4] == 'X':
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                0,
                                0,
                                count_var,
                                green_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                1,
                                1,
                                stock_valuation_list[index][0],
                                green_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                2,
                                2,
                                stock_valuation_list[index][1],
                                green_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                3,
                                3,
                                stock_valuation_list[index][2],
                                green_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                4,
                                4,
                                stock_valuation_list[index][3],
                                green_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                5,
                                5,
                                stock_valuation_list[index][4],
                                green_text,
                                )
                        elif stock_valuation_list[index][4] == 'Y':
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                0,
                                0,
                                count_var,
                                orange_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                1,
                                1,
                                stock_valuation_list[index][0],
                                orange_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                2,
                                2,
                                stock_valuation_list[index][1],
                                orange_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                3,
                                3,
                                stock_valuation_list[index][2],
                                orange_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                4,
                                4,
                                stock_valuation_list[index][3],
                                orange_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                5,
                                5,
                                stock_valuation_list[index][4],
                                orange_text,
                                )
                        elif stock_valuation_list[index][4] == 'Z':
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                0,
                                0,
                                count_var,
                                gray_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                1,
                                1,
                                stock_valuation_list[index][0],
                                gray_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                2,
                                2,
                                stock_valuation_list[index][1],
                                gray_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                3,
                                3,
                                stock_valuation_list[index][2],
                                gray_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                4,
                                4,
                                stock_valuation_list[index][3],
                                gray_text,
                                )
                            worksheet.write_merge(
                                line_var,
                                line_var,
                                5,
                                5,
                                stock_valuation_list[index][4],
                                gray_text,
                                )
                        count_var += 1
                        line_var += 1

                    fp = io.BytesIO()
                    workbook.save(fp)
                    data = base64.encodebytes(fp.getvalue())
                    IrAttachment = self.env['ir.attachment']
                    attachment_vals = {
                        'name': 'XYZ_Report.xls',
                        'res_model': 'ir.ui.view',
                        'type': 'binary',
                        'datas': data,
                        'public': True,
                        }
                    fp.close()

                    attachment = IrAttachment.search([('name', '=',
                            'XYZ_Report'), ('type', '=', 'binary'),
                            ('res_model', '=', 'ir.ui.view')], limit=1)
                    if attachment:
                        attachment.write(attachment_vals)
                    else:
                        attachment = \
                            IrAttachment.create(attachment_vals)

                    # TODO: make user error here

                    if not attachment:
                        raise UserError('There is no attachments...')

                    url = '/web/content/' + str(attachment.id) \
                        + '?download=true'
                    return {'type': 'ir.actions.act_url', 'url': url,
                            'target': 'new'}
                # else:
                #     raise UserError('There is not Found Any Stock Valuation ...'
                #                     )
