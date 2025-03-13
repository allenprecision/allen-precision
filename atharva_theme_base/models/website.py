# -*- coding: utf-8 -*-

import json
import re

from odoo import fields, models, api
from odoo.tools.translate import html_translate
from odoo.exceptions import UserError, ValidationError

class User(models.Model):
    _inherit = 'res.users'

    inquiry_data = fields.Text("Inquiry Data", store=True, default="{}")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    active_product_inquiry = fields.Boolean(string="Inquiry Submit Action",related='website_id.active_product_inquiry',readonly=False)
    inquiry_submit_action = fields.Selection(
        selection=[('email', "Send An Email"),('crm', "Create An Opportunity")], string="Product Queries Action", related="website_id.inquiry_submit_action", readonly=False)
    inquiry_recipient_id = fields.Many2one('res.users',related='website_id.inquiry_recipient_id',domain="[('share', '=', False)]",readonly=False)
    sales_person_id = fields.Many2one('res.users', related='website_id.sales_person_id', string='Salesperson', readonly=False, domain="[('share', '=', False)]")
    sales_team_id = fields.Many2one('crm.team', related='website_id.sales_team_id', string='Sales Team', readonly=False)
    inquiry_header = fields.Html("Inquery Header",  related="website_id.inquiry_header", readonly=False, translate=True)
    inquiry_desc_info = fields.Html("Inquery Information", related="website_id.inquiry_desc_info", readonly=False, translate=True)

class ShopProductPerPage(models.Model):
    _name = 'as.ppg'
    _description = "Product Per Page Dropdown Shop"
    _order = "sequence,id"

    sequence = fields.Integer(string="Sequence")
    name = fields.Integer(string="PPG", default='10', required=True)

    _sql_constraints = [("name_uniqe", "unique (name)", "Value already exists.!")]

class CustomWebsite(models.Model):
    _inherit = 'website'

    def _default_sales_team_id(self):
        team = self.env.ref('sales_team.salesteam_website_sales', False)
        if team and team.active:
            return team.id
        else:
            return None

    shop_special_offer = fields.Html(sanitize_form=False, sanitize_attributes=False, translate=html_translate)

    is_advance_megamenu = fields.Boolean(string="Active Advance Megamenu")
    advance_megamenu_id = fields.Many2one("advance.megamenu", string="Advance Megamenu", domain="[('website_id', '=', id)]")

    # Globel Settings
    active_login_popup = fields.Boolean(string="Login Popup")
    active_mini_cart = fields.Boolean(string="Mini Cart", default=True)
    active_scroll_top = fields.Boolean(string="Scroll Top", default=True)
    active_b2b_mode = fields.Boolean(string="B2B Mode", default=False)

    # Shop Page Settings
    active_shop_quick_view = fields.Boolean(string="Quick View", default=True)
    active_shop_rating = fields.Boolean(string="Rating")
    active_shop_similar_product = fields.Boolean(string="Similar Product", default=True)
    active_shop_offer_timer = fields.Boolean(string="Offer timer", default=True)
    active_shop_stock_info = fields.Boolean(string="Stock Info", default=True)
    active_shop_color_variant = fields.Boolean(string="Color Variant", default=True)
    active_shop_brand_info = fields.Boolean(string="Brand Info", default=True)
    active_shop_hover_image = fields.Boolean(string="Hover Image", default=True)
    active_shop_label = fields.Boolean(string="Shop Label", default=True)
    active_shop_clear_filter = fields.Boolean(string="Shop Clear Filter", default=True)
    active_shop_ppg = fields.Boolean(string="Shop PPG", default=True)
    active_attribute_search = fields.Boolean(string="Shop Attribute Search", default=True)
    active_stock_only = fields.Boolean(string="Shop Stock Only", default=True)
    active_load_more = fields.Boolean(string="Shop Load More", default=True)
    active_tag_filter = fields.Boolean(string="Shop Tag Filter", default=True)
    active_brand_filter = fields.Boolean(string="Shop Brand Filter", default=True)
    active_rating_filter = fields.Boolean(string="Shop Rating Filter", default=True)
    active_attribute_count = fields.Boolean(string="Shop Attribute Counter", default=True)
    active_hide_zero_attribute = fields.Boolean(string="Shop Hide Extra Attribute", default=True)
    active_shop_product_reference = fields.Boolean(string="Shop Product Reference", default=True)

    # Product Detail Setting
    active_product_label = fields.Boolean(string="Product Label", default=True)
    active_product_offer_timer = fields.Boolean(string="Product Offer Timer", default=True)
    active_product_reference = fields.Boolean(string="Product Reference", default=True)
    active_product_category = fields.Boolean(string="Product Category", default=True)
    active_product_tag = fields.Boolean(string="Product Tag", default=True)
    active_product_brand = fields.Boolean(string="Product Brand", default=True)
    active_product_advance_info = fields.Boolean(string="Product Advance Info", default=True)
    active_product_variant_info = fields.Boolean(string="Product Variant Info", default=True)
    active_product_accessory = fields.Boolean(string="Product Accessory", default=True)
    active_product_alternative = fields.Boolean(string="Product Alternative", default=True)
    active_product_pager = fields.Boolean(string="Product Pager", default=True)
    active_product_sticky = fields.Boolean(string="Product Stocky", default=True)
    active_product_bulk_save = fields.Boolean(string="Product Bulk Save", default=True)
    active_last_month_count = fields.Boolean(string="Product Last Mount sale Count", default=True)
    active_product_inquiry = fields.Boolean(string="Inquiry Submit Action")

    inquiry_submit_action = fields.Selection(
        selection=[('email', "Send An Email"),('crm', "Create An Opportunity")],string="Product Queries Action")
    sales_person_id = fields.Many2one('res.users', string='Salesperson')
    sales_team_id = fields.Many2one('crm.team',string='Sales Team', ondelete="set null",default=_default_sales_team_id)
    inquiry_recipient_id = fields.Many2one('res.users',string="Inquiry Recipient")
    inquiry_header = fields.Html("Inquery Header", default="Have Questions ?", translate=True)
    inquiry_desc_info = fields.Html("Inquery Information", default="We will follow up with you via email within 24-56 hours", translate=True)

    active_free_shipping = fields.Boolean(string="Free Shipping", default=True)

class WebsiteMenuTabs(models.Model):
    _name = "as.megamenu.tabs"
    _description = "Website Menu Tabs"

    DEFAULT_DESCRIPTION = '<section class="as_mega_menu as-mega-menu-preview-section" data-as-snippet="as_mega_menu">\
                                <div class="container as-mega-menu-welcome">\
                                    <div class="as-mm-wc-in">\
                                        <button class="btn as-e-btn-primary as-config"><i class="fa fa-pencil-square-o"/> Configure Alan Mega Menu </button>\
                                        <div class="as-mm-wc-img">\
                                            <img src="/theme_alan/static/src/img/megamenu/configure-mega-menu.svg" />\
                                        </div>\
                                    </div>\
                                </div>\
                            </section>'

    name = fields.Char(required=True)
    icon = fields.Image(max_width=100, max_height=100, required=True)
    redirect = fields.Char(string="Redirect Link", default="/", required=True)
    description = fields.Html(default=DEFAULT_DESCRIPTION, sanitize_attributes=False)

    def write(self, vals):
        res = super(WebsiteMenuTabs, self).write(vals)
        self.env.registry.clear_cache()
        return res

class WebsiteMenuAlanTags(models.Model):
    _inherit = "website.menu"

    is_tag_active = fields.Boolean(string="Menu Tag")
    tag_text_color = fields.Char(string="Tag Text Color")
    tag_bg_color = fields.Char(string="Tag Background Color")
    tag_text = fields.Char(string="Tag Text", translate=True)

    hlt_menu = fields.Boolean(string="Highlight Menu")
    hlt_menu_bg_color = fields.Char(string="Background Color")
    hlt_menu_ft_col = fields.Char(string="Font Color")
    hlt_menu_icon = fields.Char(string="Fav Icon")

    active_mega_tabs = fields.Boolean(string="Active Megamenu Tabs")
    megamenu_tabs = fields.Many2many("as.megamenu.tabs", string="Megamenu Tabs")

    is_advance_megamenu = fields.Boolean(string="Active Advance Megamenu")
    advance_megamenu_id = fields.Many2one("advance.megamenu", string="Advance Megamenu")

    @api.constrains('active_mega_tabs','is_advance_megamenu')
    def _check_unique_active_mega_menu(self):
        for rec in self:
            if rec.is_advance_megamenu == True and rec.active_mega_tabs == True:
                raise UserError("Only one active menu (MegaMenu Or Advance MegaMenu)")

    @api.model
    def get_tree(self, website_id, menu_id=None):
        website = self.env['website'].browse(website_id)

        def make_tree(node):
            menu_url = node.page_id.url if node.page_id else node.url
            menu_node = {
                'fields': {
                    'id': node.id,
                    'name': node.name,
                    'url': menu_url,
                    'new_window': node.new_window,
                    'is_mega_menu': node.is_mega_menu,
                    'sequence': node.sequence,
                    'parent_id': node.parent_id.id,
                    'tag_text': node.tag_text,
                    'is_tag_active': node.is_tag_active,
                    'tag_bg_color': node.tag_bg_color,
                    'tag_text_color': node.tag_text_color,
                    'hlt_menu': node.hlt_menu,
                    'hlt_menu_bg_color': node.hlt_menu_bg_color,
                    'hlt_menu_ft_col': node.hlt_menu_ft_col,
                    'hlt_menu_icon':node.hlt_menu_icon,
                },
                'children': [],
                'is_homepage': menu_url == (website.homepage_url or '/'),
            }
            for child in node.child_id:
                menu_node['children'].append(make_tree(child))
            return menu_node
        menu = menu_id and self.browse(menu_id) or website.menu_id
        return make_tree(menu)

    @api.onchange('is_mega_menu')
    def _onchange_is_mega_menu(self):
        if self.is_mega_menu and self.is_advance_megamenu:
            raise UserError("Only one active menu (MegaMenu Or Advance MegaMenu)")

class DataForm(models.Model):
    _inherit = 'ir.ui.view'

    def remove_unused_data_frame(self):
        frame_ids = self.env['ir.ui.view'].sudo().search([('arch_db', 'like', 'data-frame-id')]);
        lst=[]
        for object in frame_ids:
            string= object.arch_db
            x = re.findall('(?<=data-frame-id=")(.*?)"', string)
            for data in x:
                lst.append(data)

        return lst

class BlogExtend(models.Model):
    _inherit = "blog.post"

    cover_background = fields.Char(compute="_get_background_image")

    @api.depends('cover_properties')
    def _get_background_image(self):
        for i in self:
            cover_properties = json.loads(i.cover_properties)
            i.cover_background = cover_properties['background-image']

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    is_queries_mail = fields.Boolean('Website Query Mail')

    def _prepare_mail_values(self, res_ids):
        result = super()._prepare_mail_values(res_ids)
        if self.is_queries_mail:
            for key, values in result.items():
                partners = values['recipient_ids']
                email = ''
                if len(partners) > 1:
                    for partner in partners:
                        partner_id = self.env['res.partner'].sudo().browse(partner[1])
                        email = email + partner_id.email + ', '
                else:
                    for partner in partners:
                        partner_id = self.env['res.partner'].sudo().browse(partner[1])
                        email = email + partner_id.email
                values['recipient_ids'] = False
                values['email_to'] = email

        return result