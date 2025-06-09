# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class non_moving_report_excel(models.TransientModel):
    _name = "non.moving.report.excel"
    _description="non_moving_report_excel"
    
    
    excel_file = fields.Binary('Excel Report For Non Moving Product')
    file_name = fields.Char('Excel File', size=64)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
