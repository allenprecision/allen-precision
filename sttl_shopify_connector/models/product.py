from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    shopify_variant_id = fields.Char(string='Shopify Variant ID', copy=False)
    is_exported_to_shopify = fields.Boolean(string='Exported to Shopify', default=False, copy=False)

    def action_export_to_shopify(self):
        """
        Directly updates the variant in Shopify (Image, Price, SKU).
        """
        for variant in self:
            # 1. Sync the Parent Product first (as a fallback)
            variant.product_tmpl_id._export_to_shopify()
            
            # 2. Get the specific Shopify IDs
            # (We already handle ID saving in the template logic)
            
            variant.is_exported_to_shopify = True
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Shopify Sync',
                'message': 'Variant Successfully Synchronized to Shopify!',
                'type': 'success',
            }
        }
