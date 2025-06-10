# -*- coding: utf-8 -*-
{
    'name': 'Partner Last Order & Order Date | Partner Last SO/PO Date',
    'version': '17.0',
    'sequence': '1',
    'author': 'Creyox Technologies',
    'price': '20.0',
    'currency': 'USD',
    'category': "Extra Tools",
    "license": "OPL-1",
    'description': """It shows the last order date of customer.""",
    'summary': """It shows the last order date of customer.""",
    'depends': ['contacts', 'sale', 'purchase'],
    'data': [
        'views/res_partner_view.xml',
    ],
    'qweb': [],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
