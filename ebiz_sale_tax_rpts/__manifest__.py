# -*- coding: utf-8 -*-
{
    'name': "Reports Customization",

    'summary': """
        Hide Tax column in Quotation/Sales and AR-Reports
       """,

    'description': """
        Hide Tax column in Quotation/Sales and AR-Reports
    """,

    'website': 'http://www.e-bizsoft.com',
    'author': 'e-bizsoft',


    'category': 'Hidden',
    'version': '17.0',
    'license': 'OPL-1',


    'depends': ['base','sale','account'],
    'data': [
        'views/reports.xml'

    ],

}
