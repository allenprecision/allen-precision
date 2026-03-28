# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'APE FIXES',
    'version': '1.0',
    'category': 'sale',
    'license': 'OPL-1',
    'description': """
This is a module to fix some the core base things.
And to add some new generic fields
==============================================
""",
    'author': 'Confianz Global,Inc.',
    'website': 'https://www.confianzit.com',
    'depends': ['sale_management','sale_renting','stock','sale','delivery','account_reports','l10n_us_check_printing', 'stock_delivery', 'portal', 'website_sale', 'portal_rating'],
    'data': [
        'report/purchase_order.xml',
        'report/sale_report.xml',
        'report/delivery_slip.xml',
        'report/invoice.xml',
        'data/sequence.xml',
        'views/product_category.xml',
       'views/res_partner_view.xml',
       'views/sale_view.xml',
       'views/account_view.xml', #New Feature
       'views/picking_view.xml',
       'views/print_check.xml',
        'data/ir_cron.xml',
        
    # 'views/portal_templates.xml',
       # 'views/inventory_report.xml', #Not needed
       # 'views/account_account_type_view.xml', #New feature
    ],

 'assets': {
    'web.assets_frontend': [
        'ape_fixes/static/src/xml/portal_composer.xml',
        'ape_fixes/static/src/js/portal_chatter.js',
    ],
},

    'demo': [  ],
    
    'installable': True,
    'auto_install': False,
    'application': False,
    'images': [],
}
