# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.http_routing.models.ir_http import slug
from odoo.http import request
from odoo.tools.translate import html_translate

class WebsiteAdvanceMegamenu(models.Model):
    _name = 'advance.megamenu'
    _description = 'Website Advance Megamenu'
    _rec_name = "name"

    name = fields.Char('Menu Name', required=True, translate=True)
    website_id = fields.Many2one("website", string="Website", required=True)
    category_first_level = fields.One2many('as.megamenu.category', 'megamenu_id', string='First Level', domain=[('level', '=', 1)])
    category_second_level = fields.One2many('as.megamenu.category', 'megamenu_id', string='Second Level', domain=[('level', '=', 2)])
    category_third_level = fields.One2many('as.megamenu.category', 'megamenu_id', string='Third Level', domain=[('level', '=', 3)])
    category_fourth_level = fields.One2many('as.megamenu.category', 'megamenu_id', string='Fourth Level', domain=[('level', '=', 4)])

    show_category_second_level = fields.Boolean(string='Show Second Level', compute='_compute_show_second_level', store=True)
    show_category_third_level = fields.Boolean(string='Show Third Level', compute='_compute_show_third_level', store=True)
    show_category_fourth_level = fields.Boolean(string='Show Fourth Level', compute='_compute_show_fourth_level', store=True)

    menu_style = fields.Selection([
        ('simple', 'Simple'),
        ('modern', 'Modern'),
        ('clean', 'Clean'),
        ('trendy', 'Trendy'),
    ], string='Style', required=True, default='simple')

    menu_bg = fields.Selection([('color', 'Color'),('image', 'Image')], string='Background', default='color')
    menu_bg_color = fields.Char("Background Color")
    menu_ft_color = fields.Char("Font Color")
    menu_bg_img_repeat = fields.Selection([('repeat', 'Repeat'),('no-repeat', 'No-Repeat')], string='Background-Repeat ', default='repeat')
    menu_bg_image = fields.Image('Image', store=True, readonly=False)
    menu_position = fields.Selection([
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right'),
    ], string='Position', required=True, default='center')
    menu_preview = fields.Html(translate=html_translate, sanitize_form=False, sanitize_attributes=False)

    #=== CONSTRAINS ===#

    @api.constrains('category_first_level')
    def _check_category_first_level(self):
        for record in self:
            if not record.category_first_level:
                raise ValidationError("At least one record is required in the first level!")

    @api.constrains('menu_column')
    def _check_menu_column(self):
        if self.menu_column and self.menu_column<1:
            raise ValidationError("This column must be accept 1 To 6")
        if self.menu_column and self.menu_column>6:
            raise ValidationError("This column must be accept 1 To 6")


    #=== ACTION METHODS ===#

    def action_menu_preview(self):
        template = request.env['ir.ui.view']._render_template("atharva_theme_base.website_advance_megamenu",{'website_id':self.website_id,'advance_menu_id':self})
        self.menu_preview = template
        view_id = self.env.ref('atharva_theme_base.as_website_menu_preview').id
        return {
            'name': 'Menu Preview',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'advance.megamenu',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'res_id':  self.id,
        }

    #=== COMPUTE METHODS ===#

    @api.depends('category_first_level')
    def _compute_show_second_level(self):
        for menu in self:
            menu.show_category_second_level = bool(menu.category_first_level)

    @api.depends('category_second_level')
    def _compute_show_third_level(self):
        for menu in self:
            menu.show_category_third_level = bool(menu.category_second_level)

    @api.depends('category_third_level')
    def _compute_show_fourth_level(self):
        for menu in self:
            menu.show_category_fourth_level = bool(menu.category_third_level)


class MegamenuCategory(models.Model):
    _name = 'as.megamenu.category'
    _description = 'Megamenu Category'
    _rec_name = "menu_title"
    _order = 'sequence asc'


    megamenu_id = fields.Many2one('advance.megamenu', string='Mega Menu')
    website_id = fields.Many2one(related="megamenu_id.website_id", store=True)
    parent_menu_id = fields.Many2one('as.megamenu.category', string="Parent Menu",ondelete="restrict")
    child_menu_ids = fields.One2many('as.megamenu.category','parent_menu_id',string="Parent Menu")
    parent_categ_id = fields.Many2one(related="parent_menu_id.category_id")
    level = fields.Integer(string='Level')
    category_id = fields.Many2one("product.public.category",string="Categories")
    menu_title = fields.Char("Title", store=True, translate=True, required=True)
    sequence = fields.Integer(string='Sequence', default=1, help='Gives the sequence order when displaying.')

    is_menu_highlightor = fields.Boolean(string="Active Highlight")
    menu_highlightor_bg_color = fields.Char(string="Background Color")
    menu_highlightor_ft_col = fields.Char(string="Font Color")
    highlightor_menu_icon = fields.Char(string="Fav Icon")

    is_menu_tag_active = fields.Boolean(string="Active Tag")
    menu_tag_text_color = fields.Char(string="Text Color")
    menu_tag_bg_color = fields.Char(string="Background Color")
    menu_tag_text = fields.Char(string="Text", translate=True)

    menu_image = fields.Image('Image', store=True, readonly=False)

    menu_link_type = fields.Selection(selection=[('default','Default'),('custom','Custom'),('dynamic','Dynamic')], default="default", string="link Type")
    product_url = fields.Many2one('product.template', string='Product')
    brand_url = fields.Many2one('as.product.brand', string='Brand')
    page_url = fields.Many2one('website.page', string='Page')
    blog_url = fields.Many2one('blog.post', string='Blog')
    menu_url = fields.Char("URL", default="/")

    is_level_style = fields.Boolean(string="Active Style")
    menu_level_style = fields.Selection([
        ('default', 'Default'),
        ('style1', 'Style 1'),
        ('style2', 'Style 2'),
        ('style3', 'Style 3'),
        ('style4', 'Style 4'),
    ], string='Select Style')
    menu_column = fields.Integer("Column", default=3)
    image_style = fields.Selection(selection=[('as_icon','As Icon'),('full_size','Full Size')], default="as_icon", string="Image Style")

    child_count = fields.Integer("Child Tab" ,compute='_compute_child_levels', store=True)

    #=== CONSTRAINS ===#

    @api.constrains('website_id')
    def _check_unique_website_id(self):
        for record in self:
            product_website = record.product_url.website_id
            categories_website = record.category_id.website_id
            brand_website = record.brand_url.website_id
            blog_website = record.blog_url.website_id
            page_website = record.page_url.website_id

            if categories_website and (categories_website not in record.website_id):
                raise UserError("You can't change website, some categories already have defined in menus")

            if product_website and (product_website not in record.website_id):
                raise UserError("You can't change website, some products already have defined in menus")

            if brand_website and (brand_website not in record.website_id):
                raise UserError("You can't change website, some brands already have defined in menus")

            if blog_website and (blog_website not in record.website_id):
                raise UserError("You can't change website, some blogs already have defined in menus")

            if page_website and (page_website not in record.website_id):
                raise UserError("You can't change website, some pages already have defined in menus")

    #=== COMPUTE METHODS ===#

    @api.depends('child_menu_ids')
    def _compute_child_levels(self):
        for record in self:
            record.child_count = len(record.child_menu_ids)

    #=== ONCHANGE METHODS ===#

    @api.onchange('category_id')
    def _onchange_menu_title(self):
        if self.category_id:
            self.write({'menu_url': '/shop/category/%s' %(slug(self.category_id))})
            self.menu_title = self.category_id.name

    @api.onchange('product_url')
    def _onchange_product_url(self):
        if self.product_url:
            self.write({'brand_url': False, 'blog_url':False, 'page_url': False, 'menu_url': self.product_url.website_url})

    @api.onchange('brand_url')
    def _onchange_brand_url(self):
        if self.brand_url:
            self.write({'product_url': False, 'blog_url':False, 'page_url': False, 'menu_url': '/shop?brand=%s' % self.brand_url.id})

    @api.onchange('blog_url')
    def _onchange_blog_url(self):
        if self.blog_url:
            self.write({'brand_url': False, 'page_url': False, 'product_url': False, 'menu_url': self.blog_url.website_url})

    @api.onchange('page_url')
    def _onchange_page_url(self):
        if self.page_url:
            self.write({'product_url': False, 'blog_url':False, 'brand_url': False, 'menu_url': '/shop?brand=%s' % self.product_url.website_url})
