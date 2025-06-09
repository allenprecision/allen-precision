# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from datetime import date
from odoo import models, api,_
from odoo.exceptions import UserError

class stockProductReport(models.AbstractModel):
    _name = 'report.sh_all_in_one_stock_report.sh_stock_report'
    _description = 'Stock Product report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        '''Get selected data from wizard '''
        print("\n\n==============================22222222222222",data)
        data = dict(data or {})
        sh_from_date = data['sh_from_date']
        sh_to_date = data['sh_to_date']
        sh_category_ids = data['sh_category_ids']
        sh_select_product_cat = data['sh_select_product_cat']
        sh_vertical_attribute_id = data['sh_vertical_attribute_id']
        sh_horizontal_attribute_id = data['sh_horizontal_attribute_id']
        sh_product_ids = data['sh_product_ids']
        sh_company_id = self.env['res.company'].sudo().search(
            [('id', '=', data.get('sh_company_id')[0])])
        vals = []

        if sh_vertical_attribute_id and sh_horizontal_attribute_id:
            sh_current_date = date.today()

            # Prepare dict attribute with it's value

            sh_stock_move_open = self.env['stock.move'].sudo().search(
                [('date', '>=', sh_from_date), ('date', '<=', sh_current_date)])
            sh_stock_move_close = self.env['stock.move'].sudo().search(
                [('date', '>=', sh_from_date), ('date', '<=', sh_to_date)])
            horizontal_attr_list = []
            vertical_attr_list = []
            sh_horizontal_attribute_id = self.env['product.attribute'].sudo().search(
                [('id', '=', sh_horizontal_attribute_id[0])])
            sh_vertical_attribute_id = self.env['product.attribute'].sudo().search(
                [('id', '=', sh_vertical_attribute_id[0])])
            horizontal_attr_ids_list = sh_horizontal_attribute_id.value_ids.ids
            vertical_attr_ids_list = sh_vertical_attribute_id.value_ids.ids
            for i in range(0, len(sh_horizontal_attribute_id.value_ids.ids)):
                horizontal_attr_list.append(
                    sh_horizontal_attribute_id.value_ids[i].name)
            for j in range(0, len(sh_vertical_attribute_id.value_ids.ids)):
                vertical_attr_list.append(
                    sh_vertical_attribute_id.value_ids[j].name)
            category_list = []
            product_list = []
            product_attribute_dict = {}

            # Prepare vals product wise

            if sh_select_product_cat == 'product' and sh_product_ids:
                product_ids = product_ids = self.env['product.product'].sudo().search([
                    ('id', 'in', sh_product_ids), '|', ('company_id', '=', sh_company_id.id), ('company_id', '=', False)])
            else:
                product_ids = self.env['product.product'].sudo().search([
                    ('id', '>', 0), '|', ('company_id', '=', sh_company_id.id), ('company_id', '=', False)])
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

                    # Prepare vals category wise

                    if sh_select_product_cat == 'category' and sh_category_ids:
                        category_ids = self.env['product.category'].sudo().search([
                            ('id', 'in', sh_category_ids)])
                    else:
                        category_ids = self.env['product.category'].sudo().search([
                            ('id', '>', 0)])

                    if sh_select_product_cat == 'product' and product_ids:
                        move_lines = self.env['stock.move.line'].sudo().search(
                            [('product_id', '=', product.id), ('move_id', 'in', sh_stock_move_open.ids), '|', ('company_id', '=', sh_company_id.id), ('company_id', '=', False)])
                    if sh_select_product_cat == 'category' and category_ids:
                        move_lines = self.env['stock.move.line'].sudo().search(
                            [('product_id', '=', product.id), ('move_id', 'in', sh_stock_move_close.ids), '|', ('company_id', '=', sh_company_id.id), ('company_id', '=', False)])
                    if sh_select_product_cat == 'category':
                        if product.categ_id.id in category_ids.ids:
                            if product.categ_id.display_name in product_attribute_dict.keys():
                                pass
                            else:
                                category_list.append(
                                    product.categ_id.display_name)
                                product_attribute_dict[product.categ_id.display_name] = {
                                }
                    if sh_select_product_cat == 'category':
                        if product.categ_id.id in category_ids.ids:
                            if product.name in list(product_attribute_dict[product.categ_id.display_name].keys()):
                                pass
                            else:
                                product_attribute_dict[product.categ_id.display_name][product.name] = attribute_list
                                product_list.append(product.name)
                    else:
                        if product.name in product_list:
                            pass
                        else:
                            product_attribute_dict[product.name] = attribute_list
                            product_list.append(product.name)
                    print("\n\n========movelines",move_lines)
                    for order in move_lines:
                        print("\n\n====oreder",order.quantity)
                        # Stock stage wise filter

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
                    if sh_select_product_cat == 'category' and product.categ_id.id in category_ids.ids:
                        for att in product.product_template_attribute_value_ids:
                            if att.attribute_id.id == sh_horizontal_attribute_id.id:
                                x = horizontal_attr_list.index(att.name)
                            if att.attribute_id.id == sh_vertical_attribute_id.id:
                                y = vertical_attr_list.index(att.name)
                            if x > -1 and y > -1 and open_stock and close_stock:
                                product_attribute_dict[product.categ_id.display_name][product.name][y][(
                                    x*2)] = open_stock
                                product_attribute_dict[product.categ_id.display_name][product.name][y][(
                                    x*2)+1] = close_stock
                    if sh_select_product_cat == 'product':
                        for att in product.product_template_attribute_value_ids:
                            if att.attribute_id.id == sh_horizontal_attribute_id.id:
                                x = horizontal_attr_list.index(att.name)
                            if att.attribute_id.id == sh_vertical_attribute_id.id:
                                y = vertical_attr_list.index(att.name)
                            if x > -1 and y > -1 and open_stock and close_stock:
                                product_attribute_dict[product.name][y][(
                                    x*2)] = open_stock
                                product_attribute_dict[product.name][y][(
                                    x*2)+1] = close_stock
        if product_attribute_dict:
            vals.append({
                'sh_from_date': sh_from_date,
                'sh_to_date': sh_to_date,
                'sh_select_product_cat': sh_select_product_cat,
                'horizontal_attr_list': horizontal_attr_list,
                'vertical_attr_list': vertical_attr_list
            })

            # Return vals to print report

            return{
                'vals': vals,
                'stock_product': product_attribute_dict,
            }
        else:
            raise UserError(_('There is no data in between these dates.....'))
        