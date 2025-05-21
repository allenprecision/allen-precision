# -*- coding: utf-8 -*-
{
    # App information
    'name': 'Repair Custom',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'license': 'OPL-1',
    'description': """This module is used to add custom fields and logic to the repair application""",
    # Author
    'author': '',
    'website': '',
    'maintainer': '',
    # Dependencies
    'depends': ['repair', 'sale'],
    # Views
    'data': [
        'report/repair_report.xml',
        'views/repair.xml',
        'views/sale_order.xml',
    ],
    # Odoo Store Specific
    'installable': True,
    'auto_install': False,
    'application': False,
    'images': [],
}
