#!/usr/bin/python
# -*- coding: utf-8 -*-

# Part of Softhealer Technologies.

from odoo import models, fields, api
import xlwt
from odoo.exceptions import UserError
import base64
import io
from datetime import date


class AdvanceInventoryWizard(models.TransientModel):

    _name = 'sh.advance.inventory.report.wizard'
    _description = 'Advance Inventory Report Wizard'

    sh_from_date = fields.Date(string='From Date', required=True)
    sh_to_date = fields.Date(string='To Date', required=True)
    sh_product_ids = fields.Many2many(comodel_name='product.product',
            string='Product', domain=[('detailed_type', '=', 'product')])

    @api.onchange('sh_from_date', 'sh_to_date')
    def onchange_check_date(self):
        if self.sh_from_date and self.sh_to_date:
            if self.sh_from_date > self.sh_to_date:
                raise UserError('From date must be less than To date.')

    # @api.multi

    def sh_print_stock_report(self):
        datas = self.read()[0]
        res = self.env.ref('sh_all_in_one_stock_report.sh_fsn_stock_report_action'
                           ).report_action([], data=datas)
        return res

    def get_xls_report(self):
        if self.sh_product_ids:
            sh_products = self.env['product.product'
                                   ].sudo().search([('id', 'in',
                    self.sh_product_ids.ids)])
        else:
            sh_products = self.env['product.product'
                                   ].sudo().search([('id', '>', 0),('detailed_type', '=', 'product')])
        sh_current_date = date.today()
        sale_data_list = []
        if sh_products:
            for product in sh_products:
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
                scrap_qty_open = 0.0
                scrap_qty_close = 0.0
                sales_stock = 0
                scrap_stock_open = False
                scrap_qty_close = False
                stock_quant_inventory = self.env['stock.quant'
                        ].sudo().search([('product_id', '=',
                        product.id)], order='id desc', limit=1)
                if stock_quant_inventory:
                    adjustment_done = True
                stock_move = self.env['stock.move'
                        ].sudo().search([('product_id', '=',
                        product.id), ('date', '>=', self.sh_from_date),
                        ('date', '<=', sh_current_date), ('state', '=',
                        'done'), ('scrapped', '=', False)])
                if stock_move:
                    if not adjustment_done:
                        sale_order_domain_open = [('date', '>=',
                                self.sh_from_date), ('date', '<=',
                                sh_current_date), ('product_id', '=',
                                product.id), ('state', '=', 'done'),
                                ('move_id', 'in', stock_move.ids)]
                        sale_stock_order_open = \
                            self.env['stock.move.line'
                                ].sudo().search(sale_order_domain_open)
                        scrap_stock_open = self.env['stock.move'
                                ].sudo().search([('product_id', '=',
                                product.id), ('date', '>=',
                                self.sh_from_date), ('date', '<=',
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
                        if self.sh_to_date < sh_current_date:
                            sale_order_domain_close = [('date', '>',
                                    self.sh_to_date), ('date', '<=',
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
                                    self.sh_to_date), ('date', '<=',
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
                                close_stock = product.qty_available - purchase_qty + sale_qty + scrap_qty_close
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
                            ('date', '>=', self.sh_from_date),
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
                            ('date', '>', self.sh_to_date),
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
                            ('date', '>=', self.sh_from_date),
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
                            ('date', '>', self.sh_to_date),
                            ('date', '<=', sh_current_date),
                            ])
                        for adjustment in \
                            stock_adjustment_negative_open:
                            negative_qty_open += \
                                adjustment.product_uom_qty
                        for adjustment in \
                            stock_adjustment_negative_close:
                            negative_qty_close += \
                                adjustment.product_uom_qty
                        for adjustment in \
                            stock_adjustment_positive_open:
                            positive_qty_open += \
                                adjustment.product_uom_qty
                        for adjustment in \
                            stock_adjustment_positive_close:
                            positive_qty_close += \
                                adjustment.product_uom_qty
                        sale_order_domain_open = [('date', '>=',
                                self.sh_from_date), ('date', '<=',
                                sh_current_date), ('product_id', '=',
                                product.id), ('state', '=', 'done'),
                                ('move_id', 'in', stock_move.ids)]
                        sale_stock_order_open = \
                            self.env['stock.move.line'
                                ].sudo().search(sale_order_domain_open)
                        scrap_stock_open = self.env['stock.move'
                                ].sudo().search([('product_id', '=',
                                product.id), ('date', '>=',
                                self.sh_from_date), ('date', '<=',
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
                        if self.sh_to_date <= sh_current_date:
                            sale_order_domain_close = [('date', '>',
                                    self.sh_to_date), ('date', '<=',
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
                                    self.sh_to_date), ('date', '<=',
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
                                    - positive_qty_close \
                                    + negative_qty_close \
                                    + scrap_qty_close
                            else:
                                close_stock = product.qty_available \
                                    - positive_qty_close \
                                    + negative_qty_close \
                                    + scrap_qty_close
                        else:
                            close_stock = product.qty_available \
                                - positive_qty_close \
                                + negative_qty_close + scrap_qty_close
                elif self.sh_from_date > sh_current_date \
                    and self.sh_to_date > sh_current_date:
                    open_stock = product.qty_available
                    close_stock = product.qty_available
                sale_order_line_domain = [('order_id.date_order', '>=',
                        self.sh_from_date), ('order_id.date_order', '<='
                        , self.sh_to_date), ('product_id', '=',
                        product.id), ('order_id.state', '=', 'sale')]
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
                sale_data_list.append(vals)

        # ############################# XLS REPORT ###################################
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
        worksheet = workbook.add_sheet('FSN Report', bold_center)

        worksheet.col(0).width = 1500
        worksheet.col(1).width = 10000
        worksheet.col(2).width = 5000
        worksheet.col(3).width = 5000
        worksheet.col(4).width = 5000
        worksheet.col(5).width = 5000
        worksheet.col(6).width = 5000
        worksheet.col(7).width = 5000
        worksheet.write_merge(
            1,
            1,
            1,
            3,
            'FSN Report',
            bold_center,
            )
        worksheet.write_merge(
            3,
            3,
            1,
            2,
            'From Date : ' + str(self.sh_from_date),
            bold_center,
            )
        worksheet.write_merge(
            3,
            3,
            3,
            4,
            'To Date : ' + str(self.sh_to_date),
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
            'Opening Stock',
            bold_center,
            )
        worksheet.write_merge(
            6,
            6,
            3,
            3,
            'Closing Stock',
            bold_center,
            )
        worksheet.write_merge(
            6,
            6,
            4,
            4,
            'Average Stock',
            bold_center,
            )
        worksheet.write_merge(
            6,
            6,
            5,
            5,
            'Sales',
            bold_center,
            )
        worksheet.write_merge(
            6,
            6,
            6,
            6,
            'Turn Over Ratio',
            bold_center,
            )
        worksheet.write_merge(
            6,
            6,
            7,
            7,
            'FSN Analysis',
            bold_center,
            )

        if sale_data_list:
            count_var = 1
            line_var = 7
            for rec in sale_data_list:
                if rec['fsn'] == 'F':
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
                        rec['product'],
                        green_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        2,
                        2,
                        rec['open_stock'],
                        green_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        3,
                        3,
                        rec['close_stock'],
                        green_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        4,
                        4,
                        rec['avg_stock'],
                        green_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        5,
                        5,
                        rec['sale_qty'],
                        green_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        6,
                        6,
                        rec['turn_over_ratio'],
                        green_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        7,
                        7,
                        rec['fsn'],
                        green_text,
                        )
                elif rec['fsn'] == 'S':
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
                        rec['product'],
                        orange_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        2,
                        2,
                        rec['open_stock'],
                        orange_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        3,
                        3,
                        rec['close_stock'],
                        orange_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        4,
                        4,
                        rec['avg_stock'],
                        orange_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        5,
                        5,
                        rec['sale_qty'],
                        orange_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        6,
                        6,
                        rec['turn_over_ratio'],
                        orange_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        7,
                        7,
                        rec['fsn'],
                        orange_text,
                        )
                elif rec['fsn'] == 'N':
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
                        rec['product'],
                        gray_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        2,
                        2,
                        rec['open_stock'],
                        gray_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        3,
                        3,
                        rec['close_stock'],
                        gray_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        4,
                        4,
                        rec['avg_stock'],
                        gray_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        5,
                        5,
                        rec['sale_qty'],
                        gray_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        6,
                        6,
                        rec['turn_over_ratio'],
                        gray_text,
                        )
                    worksheet.write_merge(
                        line_var,
                        line_var,
                        7,
                        7,
                        rec['fsn'],
                        gray_text,
                        )
                count_var += 1
                line_var += 1

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            'name': 'FSN_Report.xls',
            'res_model': 'ir.ui.view',
            'type': 'binary',
            'datas': data,
            'public': True,
            }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'FSN_Report'),
                ('type', '=', 'binary'), ('res_model', '=', 'ir.ui.view'
                )], limit=1)
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)

        # TODO: make user error here

        if not attachment:
            raise UserError('There is no attachments...')

        url = '/web/content/' + str(attachment.id) + '?download=true'
        return {'type': 'ir.actions.act_url', 'url': url,
                'target': 'new'}
