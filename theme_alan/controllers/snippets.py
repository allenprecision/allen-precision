# -*- coding: utf-8 -*-

import json
import ast
import random
import logging

from odoo import http, _
from odoo.http import request, route

_logger = logging.getLogger(__name__)

class ThemeAlan(http.Controller):

    @route('/get_hotspot_product', auth='public', type="json", website=True)
    def getHotSpotInfo(self, product_tmpl_id=0, style="st1"):
        product_id = request.env['product.template'].sudo().browse(int(product_tmpl_id))
        template = request.env['ir.ui.view']._render_template("theme_alan.as_img_hotspot_product_popover", {
            'product':product_id,
            'style':style,
        })
        return {'template':template}

    @http.route('/select/data/fetch', auth='user', type="http", website=True)
    def select2DataFetch(self, terms=False, searchIn=False, **kwargs):
        results = []
        parent_category = kwargs.get("parent_category", 0)
        website_domain = request.website.website_domain()
        if searchIn:
            searchIn = ast.literal_eval(searchIn)
            for search in searchIn:
                if parent_category:
                    kwargs.get("parent_category", 0)
                    domain = website_domain + [('parent_id','=',int(parent_category)),('name','ilike',terms)]
                    records = request.env[search].search(domain)
                else:
                    domain = website_domain + [('name','ilike',terms)]
                    if search in ["product.template", "blog.post"]:
                        domain += [('is_published','=',True)]
                    records = request.env[search].search(domain)
                for record in records:
                    if search == "product.public.category":
                        if parent_category:
                            data = { 'id':record.id, 'name':record.name, 'modal':search,
                            'img': request.website.image_url(record, "image_256") }
                            results.append(data)
                        else:
                            # if not record.parent_id:
                            data = { 'id':record.id, 'name':record.name, 'modal':search ,
                            'img': request.website.image_url(record, "image_256")}
                            results.append(data)
                    elif search == "blog.post":
                        data = { 'id':record.id, 'name':record.display_name, 'modal':search ,
                                'img': request.website.image_url(record, "author_avatar")}
                        results.append(data)
                    else:
                        data = { 'id':record.id, 'name':record.display_name, 'modal':search ,
                                'img': request.website.image_url(record, "image_256")}
                        results.append(data)
        return json.dumps(results)

    @route('/get_template', auth='user', type="json", website=True)
    def getTemplate(self, template, context={}):
        return request.env['ir.ui.view']._render_template(template, context)

    @route('/get_select2_data', auth='user', type="json", website=True)
    def getSelect2Data(self, **kwargs):
        model = kwargs.get("model", False)
        if model:
            ids = kwargs.get("record_ids", [0])
            data = request.env[model].browse([int(i) for i in ids])
            if len(data) == 1:
                return {'id':data.id, 'text':data.display_name}
        return False

    @route('/save_user_custom_frame', auth='public', type="json", website=True)
    def saveUserFrame(self, frame=False, is_default_frame=False, default_frame_id=False, frame_config=False):
        response = {}
        name = request.env['ir.sequence'].sudo().next_by_code('as.frames.seq')
        if not is_default_frame:
            frame_id = request.env['as.snippet.frame'].create({'name':name, 'snippet_frame':frame, 'snippet_frame_html':frame})
            response.update({'frame':frame_id.id})
        else:
            response.update({'frame':default_frame_id})
        name = request.env['ir.sequence'].sudo().next_by_code('as.frame.config.seq')
        frame_config_id = request.env['as.snippet.frame.config'].create({'name':name,'snippet_frame_config':frame_config})
        response.update({'frame_config':frame_config_id.id})
        return response

    @route('/get_snippet_frame', auth='public', type="json", website=True)
    def getSnippetFrame(self, frame_id=False, frame_config=False):
        if frame_id and frame_config:
            frame_config_id = request.env['as.snippet.frame.config'].search([('id','=', int(frame_config))])
            frame = request.env['as.snippet.frame'].search([('id','=', int(frame_id))])
            return {'frame_id':frame.snippet_frame, 'frame_config':frame_config_id.snippet_frame_config}
        return { 'frame_id':False, 'frame_config':False }

    @route('/get_default_frame', auth='public', type="json", website=True)
    def getDefaultSnippetFrame(self):
        frame_ids = request.env['as.snippet.frame'].search([])
        template = request.env['ir.ui.view']._render_template("theme_alan.s_default_frame",{'frame_ids':frame_ids})
        return { 'response':template }

    @route('/delete_default_frame', auth='public', type="json", website=True)
    def deleteDefaultSnippetFrame(self, frame_id=False):
        if frame_id:
            request.env['as.snippet.frame'].search([('id','=', frame_id)]).unlink()
        return True

    @route('/get_record_detail', auth='public', type="json", website=True)
    def getDetailInfo(self, record_id=False, model=False, **kwargs):
        if record_id and model:
            rec_info = request.env[model].browse(record_id)
            if model == "blog.post":
                return {"id": rec_info.id,
                    "display_name":rec_info.display_name,
                    "image": request.website.image_url(rec_info,"author_avatar") }
            else:
                return {"id": rec_info.id,
                    "display_name":rec_info.display_name,
                    "image": request.website.image_url(rec_info,"image_1024") }

    @route('/get_records_details', auth='public', type="json", website=True)
    def getDetailsInfos(self, record_ids=[], model=False):
        if record_ids and model:
            record_ids = [int(i) for i in record_ids]
            rec_info = request.env[model].browse(record_ids)
            if model == "blog.post":
                return [{"id": rec.id, "display_name":rec.display_name,
                    "name":rec.name,
                    "image": request.website.image_url(rec,"author_avatar") }
                    for rec in rec_info ]
            else:
                return [{"id": rec.id, "display_name":rec.display_name,
                    "name":rec.name,
                    "image": request.website.image_url(rec,"image_1024") }
                    for rec in rec_info ]

    def sort_records(self, modal, sort, limit, domain, random_record=False):
        if modal in ["product.template", "blog.post"]:
            domain += [('is_published','=',True)]
        if sort:
            records = request.env[modal].search(domain, limit=limit, order=sort)
        else:
            if random_record:
                records = request.env[modal].search(domain)
                rec_lst = [{"id": rec.id, "display_name":rec.display_name,
                    "image": request.website.image_url(rec,"image_1024") }
                    for rec in records ]
                random.shuffle(rec_lst)
                return rec_lst[:16]
            else:
                records = request.env[modal].search(domain, limit=limit )
        return records

    @route('/get_quick_record', auth='public', type="json", website=True)
    def getQuickRecords(self, mode=False):
        website = request.website
        limit = 50
        from_date = 182
        website_domain = request.website.website_domain()
        if mode == "get_latest_product":
            limit = 15
            records = self.sort_records('product.template', 'create_date DESC', limit, website_domain)
        elif mode == "get_top_product":
            limit = 15
            records = self.sort_records('product.template', 'product_rating DESC', limit, website_domain)
        elif mode == "get_best_sold_product":
            limit = 15
            records = request.env['product.template']._get_best_seller_product(from_date, website.id, limit)
        elif mode == "_get_parent_category":
            website_domain = website_domain + [('parent_id','=', False)]
            records = self.sort_records('product.public.category', False, limit, website_domain)
        elif mode == "_get_a_to_z_category":
            records = self.sort_records('product.public.category', 'name ASC', limit, website_domain)
        elif mode == "_get_z_to_a_category":
            records = self.sort_records('product.public.category', 'name DESC', limit, website_domain)
        elif mode == "_get_z_to_a_brand":
            records = self.sort_records('as.product.brand', 'name DESC', limit, website_domain)
        elif mode == "_get_a_to_z_brand":
            records = self.sort_records('as.product.brand', 'name ASC', limit, website_domain)
        elif mode == "_get_random_brand":
            return self.sort_records('as.product.brand', False, limit, website_domain, True)
        elif mode == "_get_random_product":
            return self.sort_records('product.template', False, limit, website_domain, True)
        elif mode == "_get_random_category":
            return self.sort_records('product.public.category', False, limit, website_domain, True)
        elif mode == "_get_z_to_a_blog":
            records = self.sort_records('blog.post', 'name DESC', limit, website_domain)
        elif mode == "_get_a_to_z_blog":
            records = self.sort_records('blog.post', 'name ASC', limit, website_domain)
        elif mode == "_get_random_blog":
            return self.sort_records('blog.post', False, limit, website_domain, True)
        return [{"id": product_info.id, "display_name":product_info.display_name,
                "image": request.website.image_url(product_info,"image_1024") }
                for product_info in records ]

    @route('/get_mega_snippet_template', auth='public', type="json", website=True)
    def getSnipprtTemplate(self, snippet, record_ids, modal, design_editor, **kw):
        if snippet in ["MegaMenuProduct", "MegaMenuBrand"]:
            active_view = design_editor.get("active_view",'slider');
            col_item = int(design_editor.get("col_item",4));
            slider_config = {}
            if active_view == "slider":
                style = design_editor.get("slider_style",'');
                slider_config = {
                    'slidesPerView': 1.5,
                    'spaceBetween': 20,
                    'pagination': {
                    'el': ".swiper-pagination",
                        'clickable': True,
                    },
                    'breakpoints': {
                        767: {
                        'slidesPerView': 2,
                        },
                        1024: {
                        'slidesPerView': col_item,
                        },
                    },
                    'navigation': {
                        'nextEl': ".swiper-button-next",
                        'prevEl': ".swiper-button-prev",
                    },
                }
                if design_editor.get("auto_slider",False):
                    slider_config.update({'autoplay': {'delay': int(design_editor.get('slider_time',4)) * 1000}})
            else:
                style = design_editor.get("grid_style",'');
                col_item = int(12 / col_item);
            template_id = design_editor.get("template_id",False);
            product_ids = request.env[modal].browse(record_ids)
            context = {'data':product_ids, 'style':style, 'col_item':col_item}
            if design_editor.get("allow_link", False):
                context.update({'allow_link':True})
            template = request.env['ir.ui.view']._render_template(template_id, context)
            return {'template':template, 'slider_config':slider_config}
        elif snippet in ["MegaMenuCategory"]:
            active_view = design_editor.get("active_view",'slider');
            col_item = int(design_editor.get("col_item",4));
            slider_config = {}
            if active_view == "slider":
                style = design_editor.get("slider_style",'as-mm-category-slider_1');
                slider_config = {
                    'slidesPerView': 1.5,
                    'spaceBetween': 20,
                    'pagination': {
                    'el': ".swiper-pagination",
                        'clickable': True,
                    },
                    'breakpoints': {
                        767: {
                        'slidesPerView': 2,
                        },
                        1024: {
                        'slidesPerView': col_item,
                        },
                    },
                    'navigation': {
                        'nextEl': ".swiper-button-next",
                        'prevEl': ".swiper-button-prev",
                    },
                }
                if design_editor.get("auto_slider",False):
                    slider_config.update({'autoplay': {'delay': int(design_editor.get('slider_time',4)) * 1000}})

                cat_ids = request.env[modal].browse(record_ids)
                template_id = design_editor.get("template_id",'theme_alan.m_category_slider');
                context = {'data':cat_ids}
            else:
                style = design_editor.get("grid_style",'as-mm-category-grid_1');
                col_item = int(12 / col_item);
                extra_info = kw.get("extra_info", False)
                template_id = design_editor.get("template_id",'theme_alan.m_category_grid');
                data = {}
                sub_data = {}
                if extra_info:
                    for cats in extra_info:
                        parent_id = request.env[modal].browse(cats['parent'])
                        child_ids = []
                        lst = [int(i) for i in cats['childs']]
                        if len(lst):
                            child_ids = request.env[modal].browse(lst)
                        sub_data.update({parent_id: child_ids})
                    for rec in record_ids:
                        parent_id = request.env[modal].browse([rec])
                        if parent_id in sub_data.keys():
                            data.update({parent_id: sub_data[parent_id]})
                        else:
                            data.update({parent_id: []})
                else:
                    for rec in record_ids:
                        parent_id = request.env[modal].browse([rec])
                        if parent_id in sub_data.keys():
                            data.update({parent_id: sub_data[parent_id]})
                        else:
                            data.update({parent_id: []})
                context = {'data':data}
            context.update({'style':style, 'col_item':col_item})
            template = request.env['ir.ui.view']._render_template(template_id, context)
            return {'template':template, 'slider_config':slider_config}

    @route('/remove_records', auth='public', type="json", website=True)
    def getRemoveRecords(self, model, ids):
        request.env[model].browse(ids).unlink()
        return True

    @route('/get_frame', auth='public', type="json", website=True)
    def getFrame(self, frame_id=0):
        return request.env["as.snippet.frame"].browse(int(frame_id)).snippet_frame

    @route('/get_products_snippet_template', auth='public', type="json", website=True)
    def getProductSnippets(self, **kw):
        snippet_type = kw.get("snippet", False)
        website_domain = request.website.website_domain()
        return_context = {}
        if snippet_type:
            modal = kw.get("modal", "product.template")
            ids = kw.get("record_ids",[0])
            context = {}
            # if snippet_type    products_slider_lst:
            configuration = kw.get("design_editor",{})
            if snippet_type == "BestSellingProduct":
                record_ids = request.env[modal].browse(ids)
                return_context.update({'record_ids':[i.id for i in record_ids]})
            elif snippet_type == "LatestProduct":
                record_ids = request.env['product.template'].search(website_domain, limit=15, order="create_date DESC")
                return_context.update({'record_ids':[i.id for i in record_ids]})
            elif snippet_type == "BrandProduct":
                domain = website_domain + [('product_brand_id', 'in', ids)]
                record_ids = request.env['product.template'].search(domain)
                tab_ids = request.env[modal].browse(ids)
                context.update({'tab_ids':tab_ids})
            elif snippet_type == "CategoryProduct":
                domain = website_domain + [('public_categ_ids', 'in', ids)]
                record_ids = request.env['product.template'].search(domain)
                tab_ids = request.env[modal].browse(ids)
                context.update({'tab_ids':tab_ids})
            else:
                if modal == "blog.post":
                    record_ids = request.env[modal].browse(ids)
                    if not request.env.user._is_internal():
                        record_ids = [blog for blog in record_ids if blog.sudo().is_published == True]
                else:
                    record_ids = request.env[modal].browse(ids)

            template = False
            slider_config = {}
            context.update({'records':record_ids, 'configuration':configuration })
            template = request.env['ir.ui.view']._render_template(configuration.get('template_id'), context)
            # slider config
            return_context.update({'template':template ,'slider_config':slider_config})
            if configuration.get("view",False) == 'slider':
                slider_config.update({
                    'loop':configuration.get("loop"),
                    'spaceBetween': 15,
                    'slidesPerView': configuration.get("default_col_mob"),
                    'navigation': {
                        'nextEl': ".swiper-button-next",
                        'prevEl': ".swiper-button-prev",
                    },
                    'breakpoints': {
                        640: {
                        'slidesPerView': configuration.get("default_col_mob"),
                        },
                        768: {
                        'slidesPerView': configuration.get("default_col_mob"),
                        },
                        1024: {
                        'slidesPerView': configuration.get("default_col_desk"),
                        },
                        1200: {
                        'slidesPerView': configuration.get("default_col_desk"),
                        },
                    },
                    'observer': True,
                    'observeSlideChildren': True,
                    'observeParents': True,
                })
                if configuration.get("auto_slider"):
                    slider_config.update({
                        'autoplay':{ 'delay': int(configuration.get("slider_time")) * 1000,
                                    'disableOnInteraction':False }
                    })
                if configuration.get("pagination"):
                    pagination_style = {}
                    if configuration.get("pagination") == 'simple':
                        pagination_style = {
                            'el': ".swiper-pagination"
                        }
                    elif configuration.get("pagination") == 'dynamic':
                        pagination_style = {
                            'el': ".swiper-pagination",
                            'dynamicBullets': True,
                        }
                    elif configuration.get("pagination") == 'progress_bar':
                        pagination_style = {
                            'el': ".swiper-pagination",
                            'type': "progressbar",
                        }
                    elif configuration.get("pagination") == 'fraction':
                        pagination_style = {
                            'el': ".swiper-pagination",
                            'type': "fraction",
                        }
                    elif configuration.get("pagination") == 'scroll_bar':
                        pagination_style = {
                            'el': ".swiper-scrollbar",
                            'hide': True,
                        }
                    elif configuration.get("pagination") == 'coverflow':
                        pagination_style = {
                            'el': ".swiper-pagination",
                        }
                        slider_config.update({
                            "effect": "coverflow",
                            "grabCursor": True,
                            "centeredSlides": True,
                        })
                    elif configuration.get("pagination") == 'cards':
                        slider_config.update({
                            "effect": "cards",
                            "grabCursor": True,
                            "centeredSlides": True,
                        })
                    if configuration.get("pagination") == 'scroll_bar':
                        slider_config.update({'scrollbar':pagination_style })
                    else:
                        slider_config.update({'pagination':pagination_style })

                return_context.update({'slider_config':slider_config})
            return return_context
