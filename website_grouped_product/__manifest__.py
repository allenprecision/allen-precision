# -*- coding: utf-8 -*-
{
    'name': 'Website Grouped Product',
    'category': 'Website',
    'summary': """
        Website Group Product,extend your product detail page with group items
Website Bundle Product,
Website Group Product,
Ecommerce Product Bundle,
Group Products,
Advance Product Group,
Product Bundle Pack,
Combo Products,
    """,
    'license': 'OPL-1',
    'version': '1.0',
    'author': 'Atharva System',
    'website': 'https://www.atharvasystem.com',
    'support': 'support@atharvasystem.com',
    'description': """
    Extend your product detail page with group items

    """,
    'depends': ['website_sale_stock','website_sale_wishlist','website_sale_comparison', 'web', 'website_sale', ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/templates.xml'

    ],
    'assets': {
        'web.assets_frontend': [
            'website_grouped_product/static/src/js/product_add_to_cart.js',
            'website_grouped_product/static/src/js/product_configure_mixin_new.js',
            'website_grouped_product/static/src/scss/bulk.scss'
        ],
    },
    'installable': True,
    'application': True,
    'images': ['static/description/website-grouped-product.png'],
    'price': 45.00,
    'currency': 'EUR',
}
