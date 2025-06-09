#!/usr/bin/python
# -*- coding: utf-8 -*-

# Part of Softhealer Technologies.

from datetime import datetime
from odoo import models, api  ,_
from odoo.exceptions import UserError
import pytz


class XYZinventory_valuationReport(models.AbstractModel):

    _name = 'report.sh_all_in_one_stock_report.sh_xyz_report'
    _description = 'XYZ Stock Valuation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        sh_date = data['sh_date']
        timezone = pytz.timezone(self.env.user.tz or 'UTC')

        sh_date = datetime.strptime(sh_date, '%Y-%m-%d %H:%M:%S')
        sh_date = pytz.utc.localize(sh_date).astimezone(timezone)
        sh_print_date = str(sh_date).split('+')[0]
        if sh_date:
            # sh_products = self.env['product.product'
            #                        ].sudo().search([('id', '>', 0)])
            stock_valuation_records = self.env['stock.valuation.layer'].sudo().search([])
            product_ids_in_valuation = stock_valuation_records.mapped('product_id.id')
            sh_products = self.env['product.product'].sudo().search([('id', 'in', product_ids_in_valuation)])
            
            stock_valuation_list = []
            if sh_products:
                for product in sh_products:
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
                        stock_val[2] = round(100 * stock_val[1]/all_pro_total, 2)

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
                
                    if stock_valuation_list:
                        return {'stock_valuation_list': stock_valuation_list,
                                'date': sh_print_date}
                else:
                    raise UserError(_('No Data Found .....'))
                