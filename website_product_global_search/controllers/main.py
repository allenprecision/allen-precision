# -*- coding: utf-8 -*-
###############################################################################
#
#   Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#   Copyright (C) 2016-today Geminate Consultancy Services (<http://geminatecs.com>).
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import json
import logging
from datetime import datetime
from werkzeug.exceptions import Forbidden, NotFound
import string
from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.exceptions import ValidationError
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.main import TableCompute
from odoo.osv import expression


_logger = logging.getLogger(__name__)



class EbizWebsiteSaleExtend(WebsiteSale):

	def _get_search_domain(self, search, category, attrib_values, search_in_description=True):
		domains = [request.website.sale_product_domain()]
		if search:
			for srch in search.split(" "):
				subdomains = [
					[('name', 'ilike', srch)],
					[('product_variant_ids.default_code', 'ilike', srch)]
				]
				if search_in_description:
					subdomains.append([('description', 'ilike', srch)])
					subdomains.append([('description_sale', 'ilike', srch)])
				domains.append(expression.OR(subdomains))

		if category:
			domains.append([('public_categ_ids', 'child_of', int(category))])

		if attrib_values:
			attrib = None
			ids = []
			for value in attrib_values:
				if not attrib:
					attrib = value[0]
					ids.append(value[1])
				elif value[0] == attrib:
					ids.append(value[1])
				else:
					domains.append([('attribute_line_ids.value_ids', 'in', ids)])
					attrib = value[0]
					ids = [value[1]]
			if attrib:
				domains.append([('attribute_line_ids.value_ids', 'in', ids)])

		return expression.AND(domains)



	def sitemap_shop(env, rule, qs):
		if not qs or qs.lower() in '/shop':
			yield {'loc': '/shop'}

		Category = env['product.public.category']
		dom = sitemap_qs2dom(qs, '/shop/category', Category._rec_name)
		dom += env['website'].get_current_website().website_domain()
		for cat in Category.search(dom):
			loc = '/shop/category/%s' % slug(cat)
			if not qs or qs.lower() in loc:
				yield {'loc': loc}


	@http.route([])
	def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
		rating_list = request.httprequest.args.getlist('rating')
		brand_list = request.httprequest.args.getlist('brand')
		tag_list = request.httprequest.args.getlist('tag')
		request.website = request.website.with_context(brands=brand_list, rating=rating_list, tags=tag_list)
		res = super(EbizWebsiteSaleExtend, self).shop(page, category, search, min_price, max_price, ppg, **post)
		ProductAttribute = request.env['product.attribute']
		productBrands = request.env['as.product.brand']
		productTags = request.env['product.tags']
		productCat = request.env['product.public.category']
		attrib_list = request.httprequest.args.getlist('attrib')
		attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
		attributes_ids = {v[0] for v in attrib_values}
		products = res.qcontext.get("products", [])
		pricelist_context, pricelist = self._get_pricelist_context()
		website_domain = request.website.website_domain()
		filter_by_price_enabled = request.website.is_view_active('website_sale.filter_products_price')
		if filter_by_price_enabled:
			company_currency = request.website.company_id.currency_id
			conversion_rate = request.env['res.currency']._get_conversion_rate(company_currency, pricelist.currency_id,
																			   request.website.company_id,
																			   fields.Date.today())
		else:
			conversion_rate = 1

		options = {
			'displayDescription': True,
			'displayDetail': True,
			'displayExtraDetail': True,
			'displayExtraLink': True,
			'displayImage': True,
			'allowFuzzy': not post.get('noFuzzy'),
			'min_price': float(min_price) / conversion_rate,
			'max_price': float(max_price) / conversion_rate,
			'attrib_values': attrib_values,
			'display_currency': pricelist.currency_id,
		}

		if category:
			if type(category) == str:
				options.update({'category': category})
			else:
				options.update({'category': str(category.id)})

		product_count, details, fuzzy_search_term = request.website._search_with_fuzzy("products_only", search,
																					   limit=None,
																					   order=self._get_search_order(post),
																					   options=options)
		search_product = details[0].get('results', request.env['product.template']).with_context(bin_size=True)
		if products:
			attributes = ProductAttribute.search(
				[('product_tmpl_ids', 'in', search_product.ids), ('visibility', '=', 'visible')])
		else:
			attributes = ProductAttribute.browse(attributes_ids)
		variant_count = self._variant_count(search_product, attributes)
		common_domain = [('active', '=', True), ('website_id', 'in', (False, request.website.id))]
		brand_ids = productBrands.search(common_domain)
		tag_ids = productTags.search(common_domain)
		rating_count, brand_count, tag_count = self._rbt_count(search_product, brand_ids, tag_ids)
		category_count = self._category_count(website_domain, productCat, search_product)
		keep = QueryURL('/shop', category=category and int(category),
						search=search,
						attrib=attrib_list,
						min_price=min_price, max_price=max_price,
						order=post.get('order'),
						rating=rating_list,
						brand=brand_list,
						tag=tag_list)

		category_tags = False
		Category = request.env['product.public.category']
		if category:
			if type(category) == str:
				category_tags = Category.search([('parent_id', '=', category)] + website_domain)
			else:
				category_tags = Category.search([('parent_id', '=', category.id)] + website_domain)
		# Modify Ebiz-soft
		if search:
			add_qty = int(post.get('add_qty', 1))
			Category = request.env['product.public.category']
			if not search:
				if category:
					category = Category.search([('id', '=', int(category))], limit=1)
					if not category or not category.can_access_from_current_website():
						raise NotFound()
				else:
					category = Category
			else:
				category = Category

			if ppg:
				try:
					ppg = int(ppg)
					post['ppg'] = ppg
				except ValueError:
					ppg = False
			if not ppg:
				ppg = request.env['website'].get_current_website().shop_ppg or 20

			ppr = request.env['website'].get_current_website().shop_ppr or 4
			attrib_list = request.httprequest.args.getlist('attrib')
			attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
			attributes_ids = {v[0] for v in attrib_values}
			attrib_set = {v[1] for v in attrib_values}

			domain = self._get_search_domain(search, category, attrib_values)

			keep = QueryURL('/shop', search=search, attrib=attrib_list, order=post.get('order'))

			pricelist_context, pricelist = self._get_pricelist_context()

			request.context = dict(request.context, pricelist=pricelist.id, partner=request.env.user.partner_id)

			url = "/shop"
			if search:
				post["search"] = search
			if attrib_list:
				post['attrib'] = attrib_list

			Product = request.env['product.template'].with_context(bin_size=True)

			search_product = Product.search(domain, order=self._get_search_order(post))

			website_domain = request.website.website_domain()

			categs_domain = [('parent_id', '=', False)] + website_domain

			if search:
				search_categories = Category.search(
					[('product_tmpl_ids', 'in', search_product.ids)] + website_domain).parents_and_self
				categs_domain.append(('id', 'in', search_categories.ids))
			else:
				search_categories = Category

			if search:
				# for product_list in search_product:
				search_products = Product.search([(search_product, 'in', int(category))])
			elif not search_product:
				raise NotFound()

			categs = Category.search(categs_domain)
			if category:
				url = "/shop/category/%s" % slug(category)

			product_count = len(search_product)

			pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)

			offset = pager['offset']
			products = search_product[offset: offset + ppg]

			ProductAttribute = request.env['product.attribute']

			# get all products without limit
			if products:
				attributes = ProductAttribute.search([('product_tmpl_ids', 'in', search_product.ids)])
			else:
				attributes = ProductAttribute.browse(attributes_ids)

			layout_mode = request.session.get('website_sale_shop_layout_mode')

			if not layout_mode:
				if request.website.viewref('website_sale.products_list_view').active:
					layout_mode = 'list'
				else:
					layout_mode = 'grid'

			res.qcontext.update({
				'search': search,
				'category': category,
				'attrib_values': attrib_values,
				'attrib_set': attrib_set,
				'pager': pager,
				'pricelist': pricelist,
				'add_qty': add_qty,
				'products': products,
				'search_count': product_count,  # common for all searchbox
				'bins': TableCompute().process(products, ppg, ppr),
				'ppg': ppg,
				'ppr': ppr,
				'categories': categs,
				'attributes': attributes,
				'keep': keep,
				'search_categories_ids': search_categories.ids,
				'layout_mode': layout_mode,
				# 'public_categ_ids': search_products.ids,
			})
	# ____________#Modify Ebiz-soft-------------------------------------

		res.qcontext.update({
			'keep': keep,
			'attributes_ids': attributes_ids,
			'variant_count': variant_count,
			'category_tags': category_tags,
			'brand_count': brand_count,
			'modal_cat_list': [cat.id for cat in productCat.search([] + website_domain)],
			"modal_brand_list": [brand.id for brand in brand_ids],
			'category_count': category_count,
			'tag_count': tag_count,
			'sel_tag_list': tag_list,
			'alphabets': list(string.ascii_uppercase),
			'all_tag_list': tag_ids,
			'sel_brand_list': brand_list,
			'all_brand_list': brand_ids,
			'rating_count': rating_count,
			'rating': rating_list,
			'as_shop': True
		})
		return res



