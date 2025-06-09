# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name":"All In One Stock Report",
    "author":"Softhealer Technologies",
    "website":"https://www.softhealer.com",
    "support":"support@softhealer.com",
    "category":"Discuss",
    "license":"OPL-1",
    "summary":"all in one inventory reports all in one stock reports All In One Stock Report Handles The all stock related reports FSN Report FSN Inventory Report Inventory Fast Moving Product Report Slow Moving Product Report Inventory Non Moving Product Report Inventory FSN Analysis Report Fast Moving Report Slow Moving Report Non Moving Report FSN Odoo Inventory Fast Moving Products Inventory slow moving products Inventory non moving products Fast Moving stock Slow moving stock Non moving stock Product FSN Reports FSN (Fast,Slow & Non-Moving) Inventory Report FSN Report FSN Inventory Report Fast,Slow & Non-Moving Inventory Report Odoo Advance Inventory Report Stock Aging Report For Unsold Products Report Unsold Product Report Non Moving Products Report Non-Moving Product Report Non Moving Product Report Inventory Analysis Report Non-Moving Stock Report Non Moving Stock Report With PDF Non Moving Stock Report With Excel Non Moving Stock Report With XLSX Odoo Non Selling Products Report Non Non Selling Inventory Reports Non Selling Stock Reports Non Moving Inventory Reports Non Moving Item Reports Unsold Inventory Reports Unsold Stock Reports Dead Stock Reports Deadstock Reports find stock of product location give stock quantity by date provide product quantity search product by place module search product by time show forecast product quantity show on hand stock quantity incoming stock quantity Print Stock Card Report In PDF Stock Card Report In EXCEl Stock Card Report In XLS Product Stock Report Stock Rotation Report Real Time Stock In Real Time Stock Out Stock Ledger Report Incoming Ledger Outgoing Ledger Inventory Valuation Odoo Stock Movement Analysis Report Product Movement Analysis Report Stock Movement Report Inventory Movement Analysis Report Inventory Movement Report Stock Product Attribute Report Stock Product Stock Attribute Report Summary Report Category Report Variants Report Product Variant Attribute Report Product Variant Horizontal Attribute Report Vertical Attribute Report Attribute Wise Warehouse XYZ Report XYZ Stock Report Inventory XYZ Report XYZ Valuation Inventory XYZ Analysis Report XYZ Inventory Valuation Report Stock Valuation XYZ PDF Report XYZ Excel Report XYZ XLS Report XYZ Warehouse XYZ Reduce Stock Carring Cost Inventory Demand Report Odoo XYZ Inventory Report Odoo Print Report Generate Inventory Report Print Reports Print XYZ Inventory Report Print Inventory Report Classify Inventory Inventory Classification Inventory Analysis XYZ Reports  Non Moving Product Reports Non Moving Inventory Reports Non Moving Stock Reports FSN Inventory Reports Fast Selling Inventory Reports Fast Selling Stock Reports Slow Selling Stock Reports Slow Selling Inventory Reports odoo ",
    "description":"""Using our module you to generate a comprehensive range of inventory reports, including the Non-Moving Products Report, FSN (Fast, Slow & Non-Moving) Inventory Report, Stock by Location, Stock Card Report, Product Attribute-Wise Stock Report, and XYZ Inventory Report. Gain valuable insights into your stock management with ease and efficiency.""",
    "version":"0.0.1",
    "depends": ["product","sale_management","purchase","account","stock"],
    "data": [
        "sh_fsn_report/security/sh_fsn_report_groups.xml",
        "sh_fsn_report/security/ir.model.access.csv",
        "sh_fsn_report/wizard/sh_advance_inventory_wizard_views.xml",
        "sh_fsn_report/report/sh_advance_inventory_templates.xml",
        "sh_non_moving_product_report/security/sh_non_moving_product_report_groups.xml",
        "sh_non_moving_product_report/security/ir.model.access.csv",
        "sh_non_moving_product_report/wizard/sh_non_moving_product_report_wizard_views.xml",
        "sh_non_moving_product_report/report/sh_non_moving_product_report_templates.xml",
        "sh_non_moving_product_report/views/sh_non_moving_product_views.xml",
        "sh_stock_by_location/security/sh_stock_by_location_groups.xml",
        "sh_stock_by_location/security/ir.model.access.csv",
        "sh_stock_by_location/report/sh_product_stock_by_location_templates.xml",
        "sh_stock_by_location/views/product_template_views.xml",
        "sh_stock_card_report/security/sh_stock_card_groups.xml",
        "sh_stock_card_report/security/ir.model.access.csv",
        "sh_stock_card_report/wizard/sh_stock_card_report_wizard_views.xml",
        "sh_stock_card_report/report/sh_stock_card_report_templates.xml",
        "sh_stock_card_report/report/sh_stock_card_reports.xml",
        "sh_stock_product_attribute_report/security/sh_stock_product_attribute_report_groups.xml",
        "sh_stock_product_attribute_report/security/ir.model.access.csv",
        "sh_stock_product_attribute_report/wizard/sh_stock_product_attribute_wizard_views.xml",
        "sh_stock_product_attribute_report/report/sh_stock_product_attribute_report_templates.xml",
        "sh_stock_product_attribute_report/report/sh_stock_product_attribute_reports.xml",
        "sh_xyz_inventory_valuation_report/security/sh_xyz_inventory_valuation_groups.xml",
        "sh_xyz_inventory_valuation_report/security/ir.model.access.csv",
        "sh_xyz_inventory_valuation_report/wizard/sh_xyz_advance_inventory_wizard_views.xml",
        "sh_xyz_inventory_valuation_report/report/sh_xyz_advance_inventory_templates.xml",
    ],
    "application":
    True,
    "images": ["static/description/background.png", ],
    "auto_install":
    False,
    "installable":
    True,
    "price":
    178,
    "currency":
    "EUR"
}
