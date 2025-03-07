# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'APE FIXES',
    'version': '1.0',
    'category': 'sale',
    'license': 'AGPL-3',
    'description': """
This is a module to fix some the core base things.
And to add some new generic fields
==============================================
""",
    'author': 'Confianz Global,Inc.',
    'website': 'https://www.confianzit.com',
    'depends': ['sale_management','sale_renting','stock','sale','delivery','account_reports','l10n_us_check_printing'],
    'data': [
        'report/purchase_order.xml',
        'report/sale_report.xml',
        # 'report/delivery_slip.xml',
        'report/invoice.xml',
        'data/sequence.xml',
        'views/product_category.xml',
       'views/res_partner_view.xml',
       'views/sale_view.xml',
       'views/account_view.xml', #New Feature
       'views/picking_view.xml',
       'views/print_check.xml',
    'views/portal_templates.xml',
       # 'views/inventory_report.xml', #Not needed
       # 'views/account_account_type_view.xml', #New feature
    ],
    'demo': [  ],
    
    'installable': True,
    'auto_install': False,
    'application': False,
    'images': [],
}
