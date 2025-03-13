# -*- coding: utf-8 -*-

import json
import logging
import ast

import odoo
from odoo import http, _, fields
from odoo.http import request, route
from odoo.tools import lazy
import datetime
from odoo.osv import expression

from odoo.exceptions import UserError
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.utils import ensure_db
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.auth_oauth.controllers.main import OAuthLogin
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.website_sale.controllers.main import WebsiteSale, TableCompute
from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController
from odoo.addons.website.controllers.main import Website
from odoo.addons.http_routing.models.ir_http import slug
from collections import Counter
from markupsafe import Markup

_logger = logging.getLogger(__name__)

class WebsiteSaleAlanVariant(WebsiteSaleVariantController):
    @route()
    def get_combination_info_website(self, *args, **kwargs):
        res = super().get_combination_info_website(*args, **kwargs)
        res.update({'bulk_save': False})
        if "product_id" in res.keys():
            product_id = request.env['product.product'].sudo().browse(res.get("product_id", 0))
            current_pricelist = request.website._get_current_pricelist()
            if current_pricelist:
                pricelist_item_ids = current_pricelist.sudo()._get_applicable_rules(product_id, fields.Date.today())
                template = request.env['ir.ui.view']._render_template("theme_alan.bulk_save_offers",{
                            'product': product_id,
                            'pricelist_item_ids': pricelist_item_ids })

                get_offer_date = product_id._get_offer_timing(current_pricelist)
                res.update({'bulk_save': template, 'offer_timer':get_offer_date})
            res.update({'default_code':product_id.default_code, 'last_month_count': product_id.get_sale_count_last_month()})
        return res

class WebsiteSaleAlanShop(WebsiteSale):

    @http.route()
    def cart_update_json(
        self, product_id, line_id=None, add_qty=None, set_qty=None, display=True,
        product_custom_attribute_values=None, no_variant_attribute_values=None, **kw):

        res = super(WebsiteSaleAlanShop, self).cart_update_json(
            product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, display=display,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values, **kw
        )
        order = request.website.sale_get_order(force_create=True)
        res['theme_alan.as_shipping_view_template'] = request.env['ir.ui.view']._render_template(
            "theme_alan.as_shipping_view_template", {
                'website_sale_order': order,
            }
        )
        return res

    def hide_out_of_stock(self, product):
        combination = product.sudo()._get_first_possible_combination()
        combination = product.sudo()._get_combination_info(combination, add_qty=1)
        product_id = request.env['product.product'].sudo().browse([combination['product_id']])
        website = request.env['website'].get_current_website()
        if not product_id.sudo().allow_out_of_stock_order and product_id.sudo().with_context(warehouse=website._get_warehouse_available()).virtual_available < 1:
            return False
        else:
            return product.id

    def _shop_lookup_products(self, attrib_set, options, post, search, website):
        # No limit because attributes are obtained from complete product list
        product_count, details, fuzzy_search_term = website.sudo()._search_with_fuzzy("products_only", search,
                                                                               limit=None,
                                                                               order=self._get_search_order(post),
                                                                               options=options)
        search_result = details[0].get('results', request.env['product.template']).with_context(bin_size=True)
        only_stock = request.session.get("stock", False)
        if only_stock:
            search_result = request.env["product.template"].sudo().browse(list([prod_id for prod_id in map(self.hide_out_of_stock, search_result) if prod_id != False]))
        if request.httprequest.args.getlist('rating'):
            search_result = search_result.sudo().filtered(lambda x: not all(rating.sudo().is_internal for rating in x.rating_ids))

        if request.env.user._is_public():
            search_result = search_result.filtered(lambda x: x.is_published and x.sale_ok)
        return fuzzy_search_term, product_count, search_result

    def _rbt_count(self, search_product, brand_list, tag_list, attributes):
        tag_count = { tag.id: len(tag.product_template_ids.sudo().filtered(lambda x: x in search_product)) for tag in tag_list}
        attr_count = { attr.id : len(attr.pav_attribute_line_ids.mapped('product_tmpl_id').sudo().filtered(lambda x: x in search_product)) for attr in attributes.mapped('value_ids')}
        brand_count = { brand.id : len(brand.brand_product_ids.sudo().filtered(lambda x: x in search_product)) for brand in brand_list}
        rating_count = Counter(rat for prod in search_product.sudo().filtered(lambda x: not all(rating.sudo().is_internal for rating in x.rating_ids))for rat in range(1, 6)if prod.sudo().product_rating >= rat)
        rating_count.update({rating: 0 for rating in range(1, 6) if rating not in rating_count})
        return tag_count, attr_count, brand_count,rating_count

    def _count_category_products(self):
        category_count = {}
        all_categs = request.env['product.public.category'].search([('website_id', 'in', [False, request.website.id])]).sudo()
        for rec in all_categs:
            child_ids = all_categs.search([('id', 'child_of', rec.ids), ('website_id', 'in', [False, request.website.id])])
            category_count[rec.id] = len(child_ids.mapped('product_tmpl_ids').sudo().filtered(lambda x: x.is_published))
        return category_count

    @route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        # Session based PPG
        if ppg:
            request.session['ppg'] = ppg
        else:
            if request.session.get('ppg', False):
                ppg = request.session['ppg']
            else:
                ppg = False
        only_stock = request.session.get("stock", False)
        if post.get("stock", False) == 'active':
            only_stock = True
        elif post.get("stock", False) == 'inactive':
            only_stock = False
        request.session["stock"] = only_stock
        brand_list = request.httprequest.args.getlist('brand')
        rating_list = request.httprequest.args.getlist('rating')
        env_context = dict(request.env.context)
        env_context.update({ 'brands':brand_list, 'rating':rating_list})
        request.env.context = env_context

        # Calling Super
        res = super(WebsiteSaleAlanShop, self).shop(page, category, search, min_price, max_price, ppg, **post)
        url = '/shop'
        if category:
            if type(category) == str:
                url = "/shop/category/%s" % category
            else:
                url = "/shop/category/%s" % slug(category)
        as_search_prds = res.qcontext['search_product']

        # Load More
        if request.website.active_load_more:
            as_ppg = res.qcontext['ppg']
            ofst = 0
            alan_pager = request.website.pager(url=url, total=res.qcontext['search_count'], page=page, step=as_ppg, scope=res.qcontext['search_count'], url_args=post)
            for page in alan_pager.get('pages'):
                page.update(prd_ids=as_search_prds[ofst:ofst + as_ppg].ids)
                ofst += as_ppg
            res.qcontext.update({'alan_pager':alan_pager})

        # For Brands Filters
        website = request.env['website'].get_current_website()
        website_domain = website.website_domain()
        ProductBrand = request.env['as.product.brand']
        brand_ids = ProductBrand.search(expression.AND([[('brand_product_ids.is_published', '=', True)],website_domain]))
        brand_set = [int(brand) for brand in brand_list]

        # For Rating Filters
        rating_max = 1
        if len(as_search_prds.mapped("rating_avg")):
            rating_max = int(max(as_search_prds.mapped("rating_avg")))  + 1
        rating_set = [int(rating) for rating in rating_list]

        tag_count, attr_count, brand_count, rating_count = self._rbt_count(res.qcontext.get('search_product'), brand_ids, res.qcontext.get('all_tags', []), res.qcontext.get('attributes', []))
        category_count = self._count_category_products()

        res.qcontext.update({
            'stock_only':request.session["stock"],
            'ppg_list':request.env['as.ppg'].search([]),
            'as_shop':True,
            'brands':brand_ids,
            'ratings':rating_max,
            'brand_set': brand_set,
            'rating_set': rating_set,
            'category_count': category_count,
            'tag_count': tag_count,
            'rating_count': rating_count,
            'attr_count': attr_count,
            'brand_count': brand_count,
            'selected_brands': request.env['as.product.brand'].browse(brand_set),
            'selected_tags' : request.env['product.tag'].browse(res.qcontext.get('tags')),
        })
        return res

    @route('/nextpage/products', auth='public', type="json", website=True)
    def nextpage_products(self, **kw):
        if kw.get('product_ids'):
            products = request.env['product.template'].sudo()
            if kw.get('products'):
                products = request.env['product.template'].sudo().browse(kw.get('products'))
            website = request.env['website'].get_current_website()
            pricelist = website.pricelist_id
            ppg = int(request.session.get('ppg') or 20)
            ppr = int(kw.get('ppr') or 4)
            product_ids = request.env['product.template'].sudo().browse(kw.get('product_ids'))
            if request.env.user._is_public():
                product_ids = product_ids.filtered(lambda x: x.is_published and x.sale_ok)
            products |= product_ids
            fiscal_position_sudo = website.fiscal_position_id.sudo()
            products_prices = lazy(lambda: product_ids._get_sales_prices(pricelist, fiscal_position_sudo))
            keep = QueryURL('/shop',)

            return request.env['ir.ui.view']._render_template("theme_alan.shop_page_next_products",{
                'bins': lazy(lambda: TableCompute().process(product_ids.sudo(), ppg, ppr)),
                'ppg':ppg,
                'ppr':ppr,
                'keep': keep,
                'products': products,
                'products_prices': products_prices,
                'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
                'products_in_wishlist': request.env['product.wishlist'].sudo().current().product_id.product_tmpl_id,
                })
        return {}

    @route('/get_similar_product', auth='public', type="json", website=True)
    def similar_product(self, **kw):
        product_id = kw.get('product_id')
        domain = expression.AND([request.website.sale_product_domain(), [('id', '=', product_id)]])
        product = request.env['product.template'].sudo().search(domain, limit=1)
        if not product:
            return False
        else:
            return request.env['ir.ui.view']._render_template("theme_alan.as_similar_product", {'products':product.alternative_product_ids})

    @route()
    def product(self, product, category='', search='', **kwargs):
        res = super(WebsiteSaleAlanShop, self).product(product, category, search, **kwargs)
        res.qcontext.update({'as_product_detail':True})
        domain = request.website.sale_product_domain() + [('active','=',True), ('website_published','=',True)]
        prod_lst = product.search(domain , order="website_sequence").mapped("id")
        previous_product = next_product = False
        if product.id in prod_lst:
            last_product_idx = len(prod_lst) - 1
            current_product_idx = prod_lst.index(product.id)
            if current_product_idx != last_product_idx:
                next_prod_id = prod_lst[current_product_idx + 1]
                next_product = product.browse(next_prod_id)
            if current_product_idx != 0:
                prev_prod_id = prod_lst[current_product_idx - 1]
                previous_product = product.browse(prev_prod_id)
            res.qcontext.update({'next_product':next_product,'previous_product':previous_product})
        return res

    @route('/get_quick_view', auth='public', type="json", website=True)
    def quick_view(self, **kw):
        product_id = kw.get('product_id')
        domain = expression.AND([request.website.sale_product_domain(), [('id', '=', product_id)]])
        product = request.env['product.template'].search(domain, limit=1)
        if not product:
            return False
        values = self._prepare_product_values(product, category='', search='', **kw)
        return request.env['ir.ui.view']._render_template("theme_alan.as_quick_view", values=values)

    @route('/advance/info/editor/<model("as.product.extra.info"):offer>', auth='user', type="http", website=True)
    def offer_design(self, offer):
        return request.render('theme_alan.as_product_advance_info_design', {'layout': offer})

    @route('/get_advance_info', auth='public', type="json", website=True)
    def get_advance_info(self, advance_info_id):
        offer = request.env['as.product.extra.info'].sudo().search([('id','=',advance_info_id)], limit=1)
        if offer.detail_description:
            return offer.detail_description
        return ""

    @route('/get_color_product', auth='public', type="json", website=True)
    def get_color_product(self, **kw):
        product_id = kw.get('product_id')
        domain = expression.AND([request.website.sale_product_domain(), [('id', '=', product_id)]])
        product = request.env['product.template'].sudo().search(domain, limit=1)
        if not product:
            return False
        else:
            return request.env['ir.ui.view']._render_template("theme_alan.as_color_product_dialog",{
                'product':product,
                'product_variant':product.product_variant_ids,
            })

    @http.route(['/product_queries'], type="json", auth='public', website=True)
    def product_queries(self, **kw):
        user_obj = request.env['res.partner'].sudo().search([['id', '=',request.env.user.partner_id.id]])
        user = request.env.user.sudo()
        produt_date_time_dict = {}
        now = datetime.datetime.now()
        product_id = kw.get('product_id')
        product = request.env['product.template'].sudo().search([('id','=',product_id)])
        product_id = product.id
        inquiry_data = ast.literal_eval(user.inquiry_data or '{}')
        if not inquiry_data:
            context = {'user_id':user_obj.id,'user_name':user_obj.name, 'user_email': user_obj.email}
            return request.env['ir.ui.view']._render_template("theme_alan.as_product_queries",context)
        else:
            if str(product.id) in list(inquiry_data.keys())  and inquiry_data.get(str(product_id)):
                date_time_compare = datetime.datetime.strptime(inquiry_data.get(str(product_id)), "%Y-%m-%d %H:%M:%S.%f")
                if date_time_compare >= now:
                    return False
                else:
                    context = {'user_id':user_obj.id,'user_name':user_obj.name, 'user_email': user_obj.email}
                    return request.env['ir.ui.view']._render_template("theme_alan.as_product_queries",context)
            else:
                context = {'user_id':user_obj.id,'user_name':user_obj.name, 'user_email': user_obj.email}
                return request.env['ir.ui.view']._render_template("theme_alan.as_product_queries",context)

    @http.route(['/send_queries_mail'], type="json", auth='public', website=True)
    def product_queries_send_mail(self,**kw):

        template = request.env.ref('theme_alan.email_template_product_queries')
        partner_id = request.env['res.partner'].sudo().search([['id', '=',kw.get('user_id')]])

        res_config = request.website.inquiry_submit_action
        user_question = kw.get('message')
        user_email =  kw.get('email')
        product_id = kw.get('product_id')
        contact_preference = kw.get('contact_preference')
        product = request.env['product.template'].sudo().search([('id','=',product_id)])

        user = request.env.user.sudo()

        produt_date_time_dict = {}

        now = datetime.datetime.now()
        product_id = product.id
        time_after_24_hours = now + datetime.timedelta(hours=24)
        inquiry_data = ast.literal_eval(user.inquiry_data or '{}')

        if str(product.id) in list(inquiry_data.keys()):
            produt_date_time_update = {str(product_id): str(time_after_24_hours)}
            inquiry_data.update(produt_date_time_update)
            user.inquiry_data = inquiry_data
        else:
            inquiry_data[product_id] = str(time_after_24_hours)
            updated_inquiry_data = json.dumps(inquiry_data)
            user.inquiry_data = updated_inquiry_data

        if contact_preference  == "Both":
            contact_preference = "Email OR Phone"

        crm_description = Markup('<h3>Product Inquiry - Your Assistance Needed</h3><br/><div>Product Name : %s</div><div>Question : %s</div><div>Contact Preference : %s</div>') % (product.name,user_question,contact_preference)

        if res_config == 'crm':
            sales_team_id = request.website.sales_team_id
            sales_person_id = request.website.sales_person_id
            if sales_team_id and sales_person_id:
                request.env['crm.lead'].sudo().create({
                'team_id':sales_team_id.id,
                'name': 'Product Inquiry',
                'email_from': user_email,
                'user_id':sales_person_id.id,
                'partner_id':partner_id.id,
                'description':crm_description,
            })

        if template and res_config == 'email':
            user_id = request.website.sudo().inquiry_recipient_id
            composer = request.env['mail.compose.message'].sudo().with_context(
                    message = user_question,
                    product = product.name,
                    partner_name = user_id.partner_id.name,
                    contact_preference = contact_preference,
                    default_force_send=True,
                    default_composition_mode='mass_mail',
                    default_model='res.partner',
                    default_res_ids=user_id.partner_id.ids,
                    default_template_id=template.id,
                    email_to=user_id.partner_id.email,
                    default_is_queries_mail = True
                ).create({
                    'message_type':'comment',
                })
            composer.sudo()._action_send_mail()

class AlanShops(http.Controller):

    @route(['/shop/brands', '/shop/brands/page/<int:page>'], type='http', auth="public", website=True)
    def BrandPage(self, page=0):
        domain = ['&',('active','=',True), ('website_id', 'in', (False, request.website.id))]
        brands = request.env['as.product.brand'].sudo().search(domain, order="name asc")
        total = brands.sudo().search_count([])
        pager = request.website.pager(
            url='/shop/brands',
            total=total,
            page=page,
            step=30,
        )
        offset = pager['offset']
        brands = brands[offset: offset + 30]
        return request.render("theme_alan.brand_list", {'brands':brands, 'pager': pager})

    @route('/get_mini_cart', auth='public', type="json", website=True)
    def mini_cart(self, **kw):
        order = request.website.sale_get_order()
        suggested_products = order.website_order_line.sudo().product_id.mapped('accessory_product_ids').filtered(lambda x: (x.is_published and x.sale_ok) and x.allow_out_of_stock_order)
        context = {'website_sale_order': order,'suggested_products':suggested_products}
        value = { 'as_mini_cart_lines':request.env["ir.ui.view"]._render_template("theme_alan.as_mini_cart_lines", context),'as_mini_cart': request.env["ir.ui.view"]._render_template("theme_alan.as_mini_cart", context)}
        return value

    @route('/as_clear_cart', type="json", auth="public", website=True)
    def as_clear_cart(self, **kw):
        order = request.website.sale_get_order()
        request.session['website_sale_cart_quantity'] = 0
        order.unlink()
        return {'empty_mini_cart': request.env["ir.ui.view"]._render_template("theme_alan.as_empty_mini_cart")}

    @route('/get_alan_configuration', auth='public', type="json", website=True)
    def get_alan_configuration(self, **kw):
        website = request.website
        data = {
            'active_login_popup':website.active_login_popup,
            'active_mini_cart':website.active_mini_cart,
            'active_scroll_top':website.active_scroll_top,
            'active_b2b_mode':website.active_b2b_mode,

            'active_shop_quick_view': website.active_shop_quick_view,
            'active_shop_rating': website.active_shop_rating,
            'active_shop_similar_product': website.active_shop_similar_product,
            'active_shop_offer_timer': website.active_shop_offer_timer ,
            'active_shop_color_variant': website.active_shop_color_variant,
            'active_shop_stock_info': website.active_shop_stock_info,
            'active_shop_brand_info': website.active_shop_brand_info,
            'active_shop_hover_image':website.active_shop_hover_image,
            'active_shop_label':website.active_shop_label,
            'active_shop_clear_filter':website.active_shop_clear_filter,
            'active_shop_ppg':website.active_shop_ppg,
            'active_stock_only':website.active_stock_only,
            'active_load_more':website.active_load_more,
            'active_brand_filter':website.active_brand_filter,
            'active_rating_filter':website.active_rating_filter,
            'active_attribute_count':website.active_attribute_count,
            'active_attribute_search':website.active_attribute_search,
            'active_hide_zero_attribute':website.active_hide_zero_attribute,
            'active_shop_product_reference':website.active_shop_product_reference,

            'active_product_label':website.active_product_label,
            'active_product_offer_timer':website.active_product_offer_timer,
            'active_product_reference':website.active_product_reference,
            'active_product_category':website.active_product_category,
            'active_product_brand':website.active_product_brand,
            'active_product_advance_info':website.active_product_advance_info,
            'active_product_variant_info':website.active_product_variant_info,
            'active_product_accessory':website.active_product_accessory,
            'active_product_alternative':website.active_product_alternative,
            'active_product_pager':website.active_product_pager,
            'active_product_sticky':website.active_product_sticky,
            'active_product_bulk_save':website.active_product_bulk_save,
            'active_last_month_count': website.active_last_month_count,
            'active_product_inquiry': website.active_product_inquiry,
            'active_free_shipping':website.active_free_shipping,
        }
        return data

    @route('/set_alan_configuration', auth='public', type="json", website=True)
    def set_alan_configuration(self, is_active, setting):
        request.website.write({ setting: is_active })
        return True

class LoginPopup(Home):

    @route('/get_login_popup', type='json', auth="public", website=True)
    def alan_login_popup(self, **kwargs):
        context = {}
        providers = OAuthLogin.list_providers(self)
        context.update(super().get_auth_signup_config())
        context.update({'providers':providers})
        signup_enabled = request.env['res.users']._get_signup_invitation_scope() == 'b2c'
        reset_password_enabled = request.env['ir.config_parameter'].sudo().get_param('auth_signup.reset_password') == 'True'
        website_logo = request.website.image_url(request.website,'logo')
        context.update({'signup_enabled':signup_enabled ,"reset_password_enabled":reset_password_enabled,'website_logo':website_logo})
        return request.env['ir.ui.view']._render_template("theme_alan.as_shop_login",context)

    @route('/alan/login/authenticate', type='json', auth="none")
    def alan_login_authenticate(self, **kwargs):
        ''' Login Authentication '''
        ensure_db()
        request.params['login_success'] = False
        if not request.uid:
            request.update_env(user=odoo.SUPERUSER_ID)
        values = request.params.copy()
        if request.httprequest.method == 'POST':
            try:
                uid = request.session.authenticate(request.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True
                request.redirect(self._login_redirect(uid, redirect=None))
                return request.params
            except odoo.exceptions.AccessDenied as e:
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')
        return values

    @route('/alan/signup/authenticate', type="json", auth="public")
    def alan_signup_authenticate(self,*args, **kw):
        ''' Signup Authentication '''
        qcontext = super(LoginPopup,self).get_auth_signup_qcontext()
        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                super(LoginPopup,self).do_signup(qcontext)
                User = request.env['res.users']
                user_sudo = User.sudo().search(
                    User._get_login_domain(qcontext.get('login')), order=User._get_login_order(), limit=1
                )
                template = request.env.ref('auth_signup.mail_template_user_signup_account_created', raise_if_not_found=False)
                if user_sudo and template:
                    template.sudo().send_mail(user_sudo.id, force_send=True)
                return {'signup_success':True}
            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                if request.env['res.users'].sudo().search([('login', '=', qcontext.get('login'))]):
                    qcontext['error'] = _('Another user is already registered using this email address.')
                else:
                    _logger.error("%s", e)
                    qcontext['error'] = _('Could not create a new account.')
        return qcontext

class B2BWebsite(Website):

    @route()
    def autocomplete(self, search_type=None, term=None, order=None, limit=5, max_nb_chars=999, options=None):
        result = super().autocomplete(search_type, term, order, limit, max_nb_chars, options)
        if request.env.user._is_public() and request.website.active_b2b_mode:
            result['parts']['is_b2b_mode'] = True
        else:
            result['parts']['is_b2b_mode'] = False
        return result

    @route()
    def hybrid_list(self, page=1, search='', search_type='all', **kw):
        result = super().hybrid_list(page, search, search_type, **kw)
        if request.env.user._is_public() and request.website.active_b2b_mode:
            result.qcontext['is_b2b_mode'] = True
        else:
            result.qcontext['is_b2b_mode'] = False
        return result