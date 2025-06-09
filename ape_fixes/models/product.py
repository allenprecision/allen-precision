# -*- coding: utf-8 -*-

from optparse import Values
# from signal import valid_signals
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import pandas as pd
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_url = fields.Char()
    product_sku = fields.Char()

    @api.constrains('default_code')
    def _check_default_code(self):
        for rec in self:
            if rec.default_code:
                p_id = rec.search([('default_code', '=', rec.default_code), ('id', 'not in', [rec.id])])
                if p_id:
                    raise UserError(
                        _(f'Internal Reference {rec.default_code} already exist in product {p_id.display_name}'))

    def move_website_description(self):
        templates = self.search([
            ('website_description', '!=', False),
            ('website_description', '!=', '')
        ])
        for template in templates:
            template.description_ecommerce = template.website_description
            template.website_description = False


class ProductDescriptionUpdater(models.TransientModel):
    _name = 'product.description.updater'
    _description = 'Updates product_description_tab from Excel'

    @api.model
    def update_product_descriptions(self):
        file_path = 'src/user/ape_fixes/models/Product_Description_ID.csv'

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            _logger.error(f"Failed to read CSV file: {e}")
            return

        # Split the DataFrame into two halves
        half_len = len(df) // 2
        df_first_half = df.iloc[:half_len]
        df_last_half = df.iloc[half_len:]

        # Use df_first_half for updating records
        for _, row in df_last_half.iterrows():
            product_id = int(row.get('ID', 0))
            description = row.get('Description Tab', '')

            if product_id:
                product = self.env['product.template'].browse(product_id)
                if product.exists():
                    product.sudo().write({'product_tab_description': description})


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_product_multiline_description_sale(self):
        """ Compute a multiline description of this product, in the context of sales
                (do not use for purchases or other display reasons that don't intend to use "description_sale").
            It will often be used as the default description of a sale order line referencing this product.
        """
        name = self.display_name
        if self.description_sale:
            name = self.description_sale if not self.default_code else f'[{self.default_code}] {self.description_sale}'

        return name

    @api.constrains('default_code')
    def _check_default_code(self):
        for rec in self:
            if rec.default_code:
                p_id = rec.search([('default_code', '=', rec.default_code), ('id', 'not in', [rec.id])])
                if p_id:
                    raise UserError(
                        _(f'Internal Reference {rec.default_code} already exist in product {p_id.display_name}'))

    @api.model
    def create(self, vals):
        # print(vals)
        res = super(ProductProduct, self).create(vals)
        if not res.default_code:
            seq_date = None
            prefix = ''
            if res.categ_id:
                categ_id = res.categ_id
                if categ_id.product_prefix:
                    prefix = categ_id.product_prefix
            res.default_code = f"{prefix}{self.env['ir.sequence'].next_by_code('product.template', sequence_date=seq_date) or _('New')}"
        return res


class ProductCategory(models.Model):
    _inherit = 'product.category'

    product_prefix = fields.Char(string='Product Reference Prefix')
