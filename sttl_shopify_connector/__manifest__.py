{
    'name': 'Shopify Odoo Connector',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Export Odoo products to Shopify with SKU and Images',
    'description': """
        This module allows you to sync Odoo products to your Shopify store.
        - Supports SKU (Internal Reference) sync.
        - Supports Image sync.
        - Configure multiple Shopify instances.
    """,
    'author': 'Antigravity',
    'depends': ['product', 'stock', 'sale_management', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/shopify_instance_views.xml',
        'views/product_template_views.xml',
        'views/product_public_category_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
