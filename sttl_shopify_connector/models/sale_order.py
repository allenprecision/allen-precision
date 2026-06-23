from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)
