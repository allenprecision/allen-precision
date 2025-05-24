# -*- coding: utf-8 -*-

from odoo import models, fields, api ,_
import logging
from datetime import datetime
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"


    # @api.returns('self', lambda value: value.id)
    # def copy(self, default=None):
    #     default = dict(default or {})
    #     seq_date = None
    #     if 'name' not in default:
    #         default['name'] = _("%s (Copy)") % self.name
    #     if 'ref' not in default:
    #          self.get_partner_ref()
    #
    #     return super(ResPartner, self).copy(default=default)

    def get_partner_ref(self):
        self.ensure_one()
        if not self.type == 'delivery':
            seq_date = None
            prefix = ''

            if self.contact_type == 'ven':
                prefix = 'V'
                self.supplier_rank = 1
                self.ref=f"{prefix}{self.env['ir.sequence'].next_by_code('res.partner.vendor', sequence_date=seq_date) or _('New')}"
            elif self.contact_type == 'cust':
                prefix = 'C'
                self.customer_rank = 1
                self.ref = f"{prefix}{self.env['ir.sequence'].next_by_code('res.partner.customer', sequence_date=seq_date) or _('New')}"
            else:
                self.ref=''


    #
    # def write(self, vals):
    #     # Limitation: renaming a sparse field or changing the storing system is
    #     # currently not allowed
    #     self.get_partner_ref()
    #     return super(ResPartner, self).write(vals)















    @api.model
    def create(self, vals):
        res = super(ResPartner,self).create(vals)
        if not res.ref and not res.type == 'delivery' and res.contact_type  in ['cust','ven']:
            seq_date = None
            prefix = ''


            if res.customer_rank and res.customer_rank > 0 and not res.parent_id:
                prefix='C'
                res.contact_type = 'cust'
                res.ref =f"{prefix}{self.env['ir.sequence'].next_by_code('res.partner.customer', sequence_date=seq_date) or _('New')}"

            elif res.supplier_rank and res.supplier_rank > 0 and not res.parent_id:
                prefix = 'V'
                res.contact_type = 'ven'
                res.ref =f"{prefix}{self.env['ir.sequence'].next_by_code('res.partner.vendor', sequence_date=seq_date) or _('New')}"

            else:
                if res.contact_type == 'cust':
                    res.customer_rank = 1
                    prefix='C'
                    res.ref =f"{prefix}{self.env['ir.sequence'].next_by_code('res.partner.customer', sequence_date=seq_date) or _('New')}"

                else:
                    res.supplier_rank = 1
                    prefix = 'V'
                    res.ref =f"{prefix}{self.env['ir.sequence'].next_by_code('res.partner.vendor', sequence_date=seq_date) or _('New')}"


        return res

    ref = fields.Char(string='Reference',track_visibility='always',index=True)
    contact_1 = fields.Char(string='Contact 1',track_visibility='always')
    
    contact_2 = fields.Char(string='Contact 2',track_visibility='always')
    customer_type = fields.Selection([('Regular','Regular'),('Resale','Resale'),('Government','Government'),('School','School'),('PLS/ENG','PLS/ENG'),('Construction','Construction'),('Other','Other'),('VENDOR','VENDOR')],string='Customer Type',track_visibility='always')
    contact_type = fields.Selection([('cust','Customer'),('ven','Vendor')],track_visibility='always')
    name = fields.Char(track_visibility='always')
    credit_limit = fields.Float(track_visibility='always')
    property_payment_term_id = fields.Many2one('account.payment.term',track_visibility='always')
    property_account_position_id = fields.Many2one('account.fiscal.position',track_visibility='always')
    property_payment_method_id = fields.Many2one(comodel_name='account.payment.method',track_visibility='always')
    property_account_payable_id = fields.Many2one('account.account',track_visibility='always')
    property_account_receivable_id = fields.Many2one('account.account',track_visibility='always')
    property_stock_customer = fields.Many2one('stock.location',track_visibility='always')
    property_stock_supplier = fields.Many2one('stock.location',track_visibility='always')
    street = fields.Char(track_visibility='always')
    street2 = fields.Char(track_visibility='always')
    zip = fields.Char(track_visibility='always')
    city = fields.Char(track_visibility='always')
    state_id = fields.Many2one("res.country.state", track_visibility='always')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', track_visibility='always')
    country_code = fields.Char(related='country_id.code', string="Country Code", track_visibility='always')
    partner_latitude = fields.Float(track_visibility='always')
    partner_longitude = fields.Float(track_visibility='always')
    phone = fields.Char(track_visibility='always')
    mobile = fields.Char(track_visibility='always')
    user_id = fields.Many2one('res.users', track_visibility='always')
    team_id = fields.Many2one('crm.team', track_visibility='always')
    property_product_pricelist = fields.Many2one('product.pricelist', track_visibility='always')
    box_1099_id = fields.Many2one("l10n_us.1099_box", track_visibility='always')
    property_delivery_carrier_id = fields.Many2one('delivery.carrier', track_visibility='always')
    website_id = fields.Many2one('website', track_visibility='always')
    property_supplier_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True,string='Vendor Payment Terms',domain="[('company_id', 'in', [current_company_id, False])]",help="This payment term will be used instead of the default one for purchase orders and vendor bills",track_visibility='always')






