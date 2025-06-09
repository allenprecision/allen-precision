# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

import datetime
from odoo import fields, models
from odoo.exceptions import UserError
from datetime import datetime
import base64
# import xlwt
import io
import xlwt


class ProductStockByLocation(models.Model):
    _name = 'product.stock.by.location'
    _description = 'Product Stock by Location'

    location = fields.Char(string="Location")

    on_hand = fields.Float("On Hand")
    forecasted = fields.Float("Forecasted")
    incoming = fields.Float("Incoming")
    outgoing = fields.Float("Outgoing")

    product_template_id = fields.Many2one(
        "product.template", "Product Template Id")
    product_variant_id = fields.Many2one(
        "product.product", "Product Variant Id")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_stock_location_ids = fields.Many2many(
        "product.stock.by.location", string="Product Stock", compute='_compute_location_wise_stock')
    prod_var = fields.Boolean(
        "Compute Product Variant", compute="_compute_product_variant")
    stock_from_date = fields.Date("Start Date")
    stock_to_date = fields.Date("End Date")

    def _compute_product_variant(self):
        if self:
            for rec in self:
                rec.prod_var = True

    def _compute_location_wise_stock(self):
        stock_location_search = self.env['stock.location'].sudo().search(
            [('usage', '=', 'internal'),('company_id','in',self.env.companies.ids)])
        product_stock_line = []
        if self and stock_location_search:
            for record in stock_location_search:
                if self.stock_from_date and self.stock_to_date:
                    res = self.sudo().with_context({'location': record.id})._compute_quantities_dict(self._context.get(
                        'lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self.stock_from_date, self.stock_to_date)

                elif self.stock_from_date and not self.stock_to_date:
                    res = self.sudo().with_context({'location': record.id})._compute_quantities_dict(self._context.get(
                        'lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self.stock_from_date, self._context.get('to_date'))

                elif self.stock_to_date and not self.stock_from_date:
                    res = self.sudo().with_context({'location': record.id})._compute_quantities_dict(self._context.get(
                        'lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self.stock_to_date)

                else:
                    res = self.sudo().with_context({'location': record.id})._compute_quantities_dict(self._context.get('lot_id'), self._context.get(
                        'owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))
                vals = {'location': record.display_name, 'on_hand': res[self.id]['qty_available'], 'forecasted': res[self.id]['virtual_available'],
                        'incoming': res[self.id]['incoming_qty'], 'outgoing': res[self.id]['outgoing_qty'], 'product_variant_id': self.id}

                var_obj = self.env['product.stock.by.location'].sudo().create(
                    vals)
                product_stock_line.append(var_obj.id)

            self.product_stock_location_ids = product_stock_line

    def location_wise_stock(self):
        self._compute_location_wise_stock()

    def print_location_wise_stock(self):

        stock_location_search = self.env['stock.location'].sudo().search(
            [('usage', '=', 'internal')])
        stock_vals = []

        if self and stock_location_search:
            for record in stock_location_search:

                if self.stock_from_date and self.stock_to_date:
                    res = self.with_context({'location': record.id})._compute_quantities_dict(self._context.get(
                        'lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self.stock_from_date, self.stock_to_date)

                elif self.stock_from_date and not self.stock_to_date:
                    res = self.with_context({'location': record.id})._compute_quantities_dict(self._context.get('lot_id'), self._context.get(
                        'owner_id'), self._context.get('package_id'), self.stock_from_date, self._context.get('to_date'))

                elif self.stock_to_date and not self.stock_from_date:
                    res = self.with_context({'location': record.id})._compute_quantities_dict(self._context.get('lot_id'), self._context.get(
                        'owner_id'), self._context.get('package_id'), self._context.get('from_date'), self.stock_to_date)

                else:
                    res = self.with_context({'location': record.id})._compute_quantities_dict(self._context.get('lot_id'), self._context.get(
                        'owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))

                vals = {'location': record.display_name, 'on_hand': res[self.id]['qty_available'], 'forecasted': res[self.id]['virtual_available'],
                        'incoming': res[self.id]['incoming_qty'], 'outgoing': res[self.id]['outgoing_qty'], 'product_variant_id': self.id}

                self.env['product.stock.by.location'].create(vals)
                stock_vals.append(vals)

        if stock_vals:
            return stock_vals

    def clear_date_filter(self):
        if self:
            self.stock_from_date = ""
            self.stock_to_date = ""
    
    def print_report_xls(self):
        workbook = xlwt.Workbook()

        count_header = 8
        now=datetime.now()
        heading_format = xlwt.easyxf(
            'font:height 245,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_header = xlwt.easyxf(
            'font:height 200,bold True;align: vert center;align: horiz center; pattern: pattern solid, fore_colour gray25;'
        )
        bold = xlwt.easyxf(
            'font:height 200,bold True;align: vert center;align: horiz center;'
        )
        worksheet = workbook.add_sheet('My XLS Report')

        worksheet.write_merge(1,2, 2, 4,'Product Stock By Location',heading_format)
        report_name='Product Stock By Location'
     
        worksheet.write_merge(4,4, 0,1, "Product Name",bold)
        worksheet.write_merge(4, 4,2,3, self.name)
        worksheet.write_merge(5,5,0, 1, "Print Date ",bold)
        worksheet.write_merge(5,5, 2,3, str(now.strftime("%d-%m-%Y %H:%M:%S")))

        worksheet.write_merge(7,7, 0,3, "Location",bold_header)
        worksheet.write(7, 4, "On Hand",bold_header)
        worksheet.write(7, 5, " Forecasted ",bold_header)
        worksheet.write(7, 6, "Incoming",bold_header)
        worksheet.write(7, 7, "Outgoing",bold_header)

        for records in self.product_stock_location_ids:
                
            worksheet.write_merge(count_header,count_header, 0,3, records.location)
            worksheet.write(count_header, 4, records.on_hand)
            worksheet.write(count_header, 5,records.forecasted)
            worksheet.write(count_header, 6,records.incoming)
            worksheet.write(count_header, 7, records.outgoing)
            count_header+=1

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        fp.close()
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": report_name + '.xls',
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }

        attachment = IrAttachment.create(attachment_vals)
        #TODO: make user error here
        if not attachment:
            raise UserError('There is no attachments...')

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


    
class ProductTempalte(models.Model):
    _inherit = 'product.template'

    product_stock_location_ids = fields.Many2many(
        "product.stock.by.location", string="Product Stock", compute='_compute_location_wise_stock')
    prod_var = fields.Boolean(
        "Compute Product Variant", compute="_compute_product_template")
    stock_from_date = fields.Date("Start Date")
    stock_to_date = fields.Date("End Date")

    def _compute_product_template(self):
        if self:
            for rec in self:
                rec.prod_var = False

    def _compute_location_wise_stock(self):
        stock_location_search = self.env['stock.location'].sudo().search(
            [('usage', '=', 'internal'),('company_id','in',self.env.companies.ids)])
        product_stock_line = []

        if self and stock_location_search:
            for record in stock_location_search:

                res = self.with_context(
                    {'location': record.id})._compute_quantities_dict()
                vals = {'location': record.display_name, 'on_hand': res[self.id]['qty_available'], 'forecasted': res[self.id]['virtual_available'],
                        'incoming': res[self.id]['incoming_qty'], 'outgoing': res[self.id]['outgoing_qty'], 'product_template_id': self.id}

                var_obj = self.env['product.stock.by.location'].create(vals)
                product_stock_line.append(var_obj.id)

            self.product_stock_location_ids = product_stock_line

    def location_wise_stock(self):
        self._compute_location_wise_stock()

    def template_location_wise_stock(self):

        stock_location_search = self.env['stock.location'].sudo().search(
            [('usage', '=', 'internal')])
        stock_vals = []

        if self and stock_location_search:
            for record in stock_location_search:

                res = self.with_context(
                    {'location': record.id})._compute_quantities_dict()

                vals = {'location': record.display_name, 'on_hand': res[self.id]['qty_available'], 'forecasted': res[self.id]['virtual_available'],
                        'incoming': res[self.id]['incoming_qty'], 'outgoing': res[self.id]['outgoing_qty'], 'product_template_id': self.id}
                self.env['product.stock.by.location'].create(vals)
                stock_vals.append(vals)

        if stock_vals:
            return stock_vals

    def clear_date_filter(self):
        if self:
            self.stock_from_date = ""
            self.stock_to_date = ""

    def print_report_xls(self):
        workbook = xlwt.Workbook()

        count_header = 8
        now=datetime.now()
        heading_format = xlwt.easyxf(
            'font:height 245,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_header = xlwt.easyxf(
            'font:height 200,bold True;align: vert center;align: horiz center; pattern: pattern solid, fore_colour gray25;'
        )
        bold = xlwt.easyxf(
            'font:height 200,bold True;align: vert center;align: horiz center;'
        )
        worksheet = workbook.add_sheet('My XLS Report')

        worksheet.write_merge(1,2, 2, 4,'Product Stock By Location',heading_format)
        report_name='Product Stock By Location'
     
        worksheet.write_merge(4,4, 0,1, "Product Name",bold)
        worksheet.write_merge(4, 4,2,3, self.name)
        worksheet.write_merge(5,5,0, 1, "Print Date ",bold)
        worksheet.write_merge(5,5, 2,3, str(now.strftime("%d-%m-%Y %H:%M:%S")))

        worksheet.write_merge(7,7, 0,3, "Location",bold_header)
        worksheet.write(7, 4, "On Hand",bold_header)
        worksheet.write(7, 5, " Forecasted ",bold_header)
        worksheet.write(7, 6, "Incoming",bold_header)
        worksheet.write(7, 7, "Outgoing",bold_header)

        for records in self.product_stock_location_ids:
                
            worksheet.write_merge(count_header,count_header, 0,3, records.location)
            worksheet.write(count_header, 4, records.on_hand)
            worksheet.write(count_header, 5,records.forecasted)
            worksheet.write(count_header, 6,records.incoming)
            worksheet.write(count_header, 7, records.outgoing)
            count_header+=1

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        fp.close()
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": report_name + '.xls',
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }

        attachment = IrAttachment.create(attachment_vals)
        #TODO: make user error here
        if not attachment:
            raise UserError('There is no attachments...')

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

