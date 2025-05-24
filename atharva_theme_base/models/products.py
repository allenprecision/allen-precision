# -*- coding: utf-8 -*-

import ast
import hashlib
from dateutil.relativedelta import relativedelta
from datetime import timedelta

from odoo import api, fields, models
from odoo.http import request
from odoo.osv import expression
from odoo.tools.translate import html_translate

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_rating = fields.Float(string='Product Rating', compute='_compute_product_rating', store=True)
    hover_image = fields.Image("Hover Image", max_width=512, max_height=512)
    product_tab_description = fields.Html(string="Description Tab", translate=html_translate, sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False,)
    doc_name = fields.Char(string="Document Name", default='Documents', required=True)
    is_active_doc = fields.Boolean(default=False, string='Show Document')
    doc_attachments = fields.Many2many("ir.attachment", string="Product Documents")
    is_unavailable_in_stock = fields.Boolean(string='Unavailable in Stock', compute='available_stock', store=True)
    product_faqs_ids = fields.Many2many("product.faqs", string="Product FAQs")
    have_color_attribute = fields.Boolean(string='Color Attribute', default=False, compute='is_contains_color_attribute', store=True)
    variant_color_images = fields.Char()

    @api.model_create_multi
    def create(self, vals_lst):
        for vals in vals_lst:
            if vals.get('doc_attachments'):
                doc_list = [i for i in vals['doc_attachments'][1]]
                attachments = self.env['ir.attachment'].sudo().browse(doc_list)
                for record in attachments:
                    if record.id in doc_list:
                        if record.public == False:
                            record.public = True
        res = super(ProductTemplate, self).create(vals_lst)
        return res

    def write(self, vals):
        if vals.get('doc_attachments'):
            doc_list = [i for i in vals['doc_attachments'][1]]
            attachments = self.env['ir.attachment'].sudo().browse(doc_list)
            for record in attachments:
                if record.id in doc_list:
                    if record.public == False:
                        record.public = True
        return super(ProductTemplate, self).write(vals)

    def get_variant_color_images(self):
        self.ensure_one()
        if self.variant_color_images:
            return ast.literal_eval(self.variant_color_images)
        else:
            return []

    @api.depends('attribute_line_ids', 'attribute_line_ids.value_ids')
    def is_contains_color_attribute(self):
        for product in self:
            for ptal in product.valid_product_template_attribute_line_ids:
                if ptal.attribute_id.display_type == 'color':
                    product.have_color_attribute = True
                    break
                else:
                    product.have_color_attribute = False

    @api.depends('virtual_available', 'allow_out_of_stock_order', 'detailed_type')
    def available_stock(self):
        for product in self:
            if product.detailed_type == 'product' and not product.allow_out_of_stock_order and product.virtual_available < 1:
                product.is_unavailable_in_stock = True
            else:
                product.is_unavailable_in_stock = False

    @api.model_create_multi
    def create(self, vals_lst):
        for vals in vals_lst:
            if vals.get('doc_attachments'):
                doc_list = [i[1] for i in vals['doc_attachments']]
                attachments = self.env['ir.attachment'].sudo().browse(doc_list)
                for record in attachments:
                    if record.id in doc_list:
                        if record.public == False:
                            record.public = True
        res = super(ProductTemplate, self).create(vals_lst)
        return res

    def write(self, vals):
        if vals.get('doc_attachments'):
            doc_list = [i[1] for i in vals['doc_attachments']]
            attachments = self.env['ir.attachment'].sudo().browse(doc_list)
            for record in attachments:
                if record.id in doc_list:
                    if record.public == False:
                        record.public = True
        return super(ProductTemplate, self).write(vals)

    @api.depends('message_ids')
    def _compute_product_rating(self):
        ''' Compute product rating '''
        for i in self:
            prodRating = round(i.sudo().rating_get_stats().get('avg') / 1 * 100) / 100
            i.product_rating = prodRating

    def _get_best_seller_product(self, from_date, website_id, limit ):
        self.env.cr.execute("""SELECT PT.id, SUM(SO.product_uom_qty),PT.website_id
                                    FROM sale_order S
                                    JOIN sale_order_line SO ON (S.id = SO.order_id)
                                    JOIN product_product P ON (SO.product_id = P.id)
                                    JOIN product_template pt ON (P.product_tmpl_id = PT.id)
                                    WHERE S.state in ('sale','done')
                                    AND (S.date_order >= %s AND S.date_order <= %s)
                                    AND (PT.website_id IS NULL OR PT.website_id = %s)
                                    AND PT.active='t'
                                    AND PT.is_published='t'
                                    GROUP BY PT.id
                                    ORDER BY SUM(SO.product_uom_qty)
                                    DESC LIMIT %s
                                """, [fields.Datetime.today() - timedelta(from_date), fields.Datetime.today(), website_id, limit])
        table = self.env.cr.fetchall()
        products = []
        for record in table:
            if record[0]:
                pro_obj = self.env[
                    'product.template'].sudo().browse(record[0])
                if pro_obj.sale_ok == True and pro_obj.is_published == True:
                    products.append(pro_obj)
        return products

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1,  parent_combination=False, only_template=False):
        res = super(ProductTemplate, self)._get_combination_info(combination, product_id, add_qty, parent_combination, only_template)
        if res.get('has_discounted_price', False):
            per = 100 - ((res['price'] /  res['list_price']) * 100)
            res.update({'as_offer_discount': "{:.2f}".format(per)})
        return res

    @api.model
    def _search_build_domain(self, domain_list, search, fields, extra=None):
        res = super(ProductTemplate, self)._search_build_domain(domain_list, search, fields, extra)
        new_domain = [res]
        if self.env.context.get('brands',[]) != []:
            new_domain.append([('product_brand_id', 'in', [int(b) for b in self.env.context['brands']])])
        if self.env.context.get('rating',[]) != []:
            new_domain.append([('rating_avg', '>=', max([int(b) for b in self.env.context['rating']]))])
        res = expression.AND(new_domain)
        return res

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_offer_timing(self, pricelist):
        common_domain = [('date_end','!=',False), ('show_timer','=',True)]
        check_global = pricelist.item_ids.search([('id','in',pricelist.item_ids.mapped('id')),('applied_on','=','3_global')] + common_domain, limit=1)
        check_category = pricelist.item_ids.search([('id','in',pricelist.item_ids.mapped('id')),('applied_on','=','2_product_category'),('categ_id','=',self.categ_id.id)] + common_domain, limit=1)
        check_product_tmpl = pricelist.item_ids.search([('id','in',pricelist.item_ids.mapped('id')),('product_tmpl_id','=',self.product_tmpl_id.id),('applied_on','=','1_product')] + common_domain, limit=1)
        check_product_varient = pricelist.item_ids.search([('id','in',pricelist.item_ids.mapped('id')),('applied_on','=','0_product_variant'), ('product_id','=',self.id)] + common_domain, limit=1)
        if check_product_varient and (fields.Datetime.today() >= check_product_varient.date_start):
            return check_product_varient.date_end
        elif check_product_tmpl and (fields.Datetime.today() >= check_product_tmpl.date_start):
            return check_product_tmpl.date_end
        elif check_category and (fields.Datetime.today() >= check_category.date_start):
            return check_category.date_end
        elif check_global and (fields.Datetime.today() >= check_global.date_start):
            return check_global.date_end
        return False

    def get_sale_count_last_month(self):
        if self.id:
            today = fields.Datetime.today()
            fc_day = today.replace(day=1)
            ldlm = fc_day - relativedelta(days=1)
            lmfd = ldlm.replace(day=1)
            domain = [
                ('state', 'in', ['sale']),
                ('product_id', '=', self.id),
                ('date', '>=', lmfd),
                ('date', '<=', ldlm),
                ('website_id', 'in', (request.website.id, False)),
            ]
            product_details = self.env['sale.report']._read_group(domain, ['product_id'], ['product_uom_qty:sum'])
            if len(product_details):
                return product_details[0][1]
        return 0

class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    pv_thumbnail = fields.Image(string="Shop Variant Image")

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            image_url = []
            if rec.attribute_id.display_type == "color":
                domain = [('attribute_id','=',rec.attribute_id.id), ('product_tmpl_id','=',rec.product_tmpl_id.id)]
                attr_lines_ids = self.sudo().search(domain)
                if attr_lines_ids:
                    for attr in attr_lines_ids:
                        if attr.pv_thumbnail:
                            sha = hashlib.sha512(str(attr.write_date).encode('utf-8')).hexdigest()[:7]
                            url = '/web/image/%s/%s/%s%s?unique=%s' % (self._name, attr.id, "pv_thumbnail", '', sha)
                            image_url.append(url)
                rec.product_tmpl_id.variant_color_images = image_url
        return res
