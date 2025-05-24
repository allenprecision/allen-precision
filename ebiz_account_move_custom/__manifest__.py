# -*- coding: utf-8 -*-
{
    # App information
    'name': 'Account Move Custom',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'license': 'OPL-1',
    'description': """This module is used to add custom fields and logic to the accounting application""",
    # Author
    'author': '',
    'website': '',
    'maintainer': '',
    # Dependencies
    'depends': ['account'],
    # Views
    'data': [
       'views/account_view.xml',
    ],
    # Odoo Store Specific
    'installable': True,
    'auto_install': False,
    'application': False,
    'images': [],
}
