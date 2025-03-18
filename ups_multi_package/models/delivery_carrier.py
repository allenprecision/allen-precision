# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import pdf
import logging
from odoo.exceptions import UserError, ValidationError
from odoo.addons.stock_delivery.models.delivery_request_objects import DeliveryCommodity, DeliveryPackage

_loggeer = logging.getLogger(__name__)


from .ups_request import Package,UPSRequest

class StockPicking(models.Model):
    _inherit='stock.picking'
    delivery_package_ids = fields.One2many('delivery.package','picking_id')    

    @api.model
    def create(self,vals):
        res = super(StockPicking,self).create(vals)
        for rec in res:
            order_id = self.env['sale.order'].sudo().search([('name','=',rec.origin)],limit=1)
            if order_id and order_id.delivery_package_ids:
                rec.delivery_package_ids=[(0,0,{'height':pack.height,'width':pack.width,'length':pack.length,'weight':pack.weight}) for pack in order_id.delivery_package_ids]
        return res
                
    
class ProviderUPS(models.Model):
    _inherit = 'delivery.carrier'

    def _get_packages_from_picking(self, picking, default_package_type):
        packages = []

        if picking.is_return_picking:
            commodities = self._get_commodities_from_stock_move_lines(picking.move_line_ids)
            weight = picking._get_estimated_weight() + default_package_type.base_weight
            packages.append(DeliveryPackage(
                commodities,
                weight,
                default_package_type,
                currency=picking.company_id.currency_id,
                picking=picking,
            ))
            return packages

        # Create all packages.
        for package in picking.package_ids:
            move_lines = picking.move_line_ids.filtered(lambda ml: ml.result_package_id == package)
            commodities = self._get_commodities_from_stock_move_lines(move_lines)
            package_total_cost = sum(
                self._product_price_to_company_currency(quant.quantity, quant.product_id, picking.company_id)
                for quant in package.quant_ids
            )
            packages.append(DeliveryPackage(
                commodities,
                package.shipping_weight or package.weight,
                package.package_type_id,
                name=package.name,
                total_cost=package_total_cost,
                currency=picking.company_id.currency_id,
                picking=picking,
            ))

        # Handle bulk weight scenario
        if picking.weight_bulk:
            commodities = self._get_commodities_from_stock_move_lines(picking.move_line_ids)
            package_total_cost = sum(
                self._product_price_to_company_currency(move_line.quantity, move_line.product_id, picking.company_id)
                for move_line in picking.move_line_ids
            )
            packages.append(DeliveryPackage(
                commodities,
                picking.weight_bulk,
                default_package_type,
                name='Bulk Content',
                total_cost=package_total_cost,
                currency=picking.company_id.currency_id,
                picking=picking,
            ))
        elif not packages:
            raise UserError(_(
                "The package cannot be created because the total weight of the "
                "products in the picking is 0.0 %s",
                picking.weight_uom_name
            ))

        # **Handle multiple delivery_package_ids properly**
        if picking.delivery_package_ids:
            packages = []  # Reset packages to create new ones from delivery_package_ids
            for delivery_package in picking.delivery_package_ids:
                commodities = self._get_commodities_from_stock_move_lines(picking.move_line_ids)
                weight = delivery_package.weight  # Ensure the correct weight is assigned per package
                package_total_cost = sum(
                    self._product_price_to_company_currency(move_line.quantity, move_line.product_id,
                                                            picking.company_id)
                    for move_line in picking.move_line_ids
                )
                package = DeliveryPackage(
                    commodities,
                    weight,  # <-- Fixed: Assigning correct weight from delivery_package
                    default_package_type,
                    name=f"Package {delivery_package.id}",
                    total_cost=package_total_cost,
                    currency=picking.company_id.currency_id,
                    picking=picking,
                )
                package.dimension['length'] = delivery_package.length
                package.dimension['width'] = delivery_package.width
                package.dimension['height'] = delivery_package.height
                packages.append(package)

        return packages
#
#
#     def ups_rate_shipment(self, order):
#         superself = self.sudo()
#         srm = UPSRequest(self.log_xml, superself.ups_username, superself.ups_passwd, superself.ups_shipper_number, superself.ups_access_number, self.prod_environment)
#         ResCurrency = self.env['res.currency']
#         max_weight = self.ups_default_package_type_id.max_weight
#         packages = []
#         total_qty = 0
#         total_weight = order._get_estimated_weight()
#         for line in order.order_line.filtered(lambda line: not line.is_delivery and not line.display_type):
#             total_qty += line.product_uom_qty
#         if order.delivery_package_ids:
#             for pack in order.delivery_package_ids:
#                 packages.append(Package(self,0.0,delivery_package=pack))
#
#         else:
#
#             if max_weight and total_weight > max_weight:
#                 total_package = int(total_weight / max_weight)
#                 last_package_weight = total_weight % max_weight
#
#                 for seq in range(total_package):
#                     packages.append(Package(self, max_weight))
#                 if last_package_weight:
#                     packages.append(Package(self, last_package_weight))
#             else:
#                 packages.append(Package(self, total_weight))
#
#         shipment_info = {
#             'total_qty': total_qty  # required when service type = 'UPS Worldwide Express Freight'
#         }
#
#         if self.ups_cod:
#             cod_info = {
#                 'currency': order.partner_id.country_id.currency_id.name,
#                 'monetary_value': order.amount_total,
#                 'funds_code': self.ups_cod_funds_code,
#             }
#         else:
#             cod_info = None
#
#         check_value = srm.check_required_value(order.company_id.partner_id, order.warehouse_id.partner_id, order.partner_shipping_id, order=order)
#         if check_value:
#
#             return {'success': False,
#                     'price': 0.0,
#                     'error_message': check_value,
#                     'warning_message': False}
#
#         ups_service_type = self.ups_default_service_type
#         result = srm.get_shipping_price(
#             shipment_info=shipment_info, packages=packages, shipper=order.company_id.partner_id, ship_from=order.warehouse_id.partner_id,
#             ship_to=order.partner_shipping_id, packaging_type=self.ups_default_package_type_id.shipper_package_code, service_type=ups_service_type,
#             saturday_delivery=self.ups_saturday_delivery, cod_info=cod_info)
#
#         if result.get('error_message'):
#             return {'success': False,
#                     'price': 0.0,
#                     'error_message': _('Error:\n%s', result['error_message']),
#                     'warning_message': False}
#
#         if order.currency_id.name == result['currency_code']:
#             price = float(result['price'])
#         else:
#             quote_currency = ResCurrency.search([('name', '=', result['currency_code'])], limit=1)
#             price = quote_currency._convert(
#                 float(result['price']), order.currency_id, order.company_id, order.date_order or fields.Date.today())
#
#         if self.ups_bill_my_account and order.partner_ups_carrier_account:
#             # Don't show delivery amount, if ups bill my account option is true
#             price = 0.0
#
#         return {'success': True,
#                 'price': price,
#                 'error_message': False,
#                 'warning_message': False}
#
#     def ups_rest_send_shipping(self, pickings):
#         res = []
#         ups = UPSRequest()
#         for picking in pickings:
#             packages, shipment_info, ups_service_type, ups_carrier_account, cod_info = self._prepare_shipping_data(picking)
#
#             check_value = ups._check_required_value(picking=picking)
#             if check_value:
#                 raise UserError(check_value)
#
#             result = ups._send_shipping(
#                 shipment_info=shipment_info, packages=packages, carrier=self, shipper=picking.company_id.partner_id, ship_from=picking.picking_type_id.warehouse_id.partner_id,
#                 ship_to=picking.partner_id, service_type=ups_service_type, duty_payment=picking.carrier_id.ups_duty_payment,
#                 saturday_delivery=picking.carrier_id.ups_saturday_delivery, cod_info=cod_info,
#                 label_file_type=self.ups_label_file_type, ups_carrier_account=ups_carrier_account)
#
#             order = picking.sale_id
#             company = order.company_id or picking.company_id or self.env.company
#             currency_order = picking.sale_id.currency_id
#             if not currency_order:
#                 currency_order = picking.company_id.currency_id
#
#             if currency_order.name == result['currency_code']:
#                 price = float(result['price'])
#             else:
#                 quote_currency = self.env['res.currency'].search([('name', '=', result['currency_code'])], limit=1)
#                 price = quote_currency._convert(
#                     float(result['price']), currency_order, company, order.date_order or fields.Date.today())
#
#             package_labels = result.get('label_binary_data', [])
#
#             carrier_tracking_ref = "+".join([pl[0] for pl in package_labels])
#             logmessage = _("Shipment created into UPS<br/>"
#                            "<b>Tracking Numbers:</b> %s<br/>"
#                            "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join([p.name for p in packages if p.name]))
#             if self.ups_label_file_type != 'GIF':
#                 attachments = [('LabelUPS-%s.%s' % (pl[0], self.ups_label_file_type), pl[1]) for pl in package_labels]
#             else:
#                 attachments = [('LabelUPS.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
#             if result.get('invoice_binary_data'):
#                 attachments.append(('UPSCommercialInvoice.pdf', result['invoice_binary_data']))
#             picking.message_post(body=logmessage, attachments=attachments)
#             shipping_data = {
#                 'exact_price': price,
#                 'tracking_number': carrier_tracking_ref}
#             res = res + [shipping_data]
#             if self.return_label_on_delivery:
#                 try:
#                     self.ups_rest_get_return_label(picking)
#                 except (UserError, ValidationError) as err:
#                     try:
#                         ups._cancel_shipping(result['tracking_ref'])
#                     except ValidationError:
#                         pass
#                     raise UserError(err)
#         return res
#
#     def ups_rest_get_return_label(self, picking, tracking_number=None, origin_date=None):
#         res = []
#         ups = UPSRequest(self)
#         packages, shipment_info, ups_service_type, ups_carrier_account, cod_info = self._prepare_shipping_data(picking)
#
#         check_value = ups._check_required_value(picking=picking, is_return=True)
#         if check_value:
#             raise UserError(check_value)
#
#         result = ups._send_shipping(
#             shipment_info=shipment_info, packages=packages, carrier=self, shipper=picking.company_id.partner_id, ship_from=picking.partner_id,
#             ship_to=picking.picking_type_id.warehouse_id.partner_id, service_type=ups_service_type, duty_payment='RECIPIENT', saturday_delivery=picking.carrier_id.ups_saturday_delivery,
#             cod_info=cod_info, label_file_type=self.ups_label_file_type, ups_carrier_account=ups_carrier_account, is_return=True)
#
#         order = picking.sale_id
#         company = order.company_id or picking.company_id or self.env.company
#         currency_order = picking.sale_id.currency_id
#         if not currency_order:
#             currency_order = picking.company_id.currency_id
#
#         if currency_order.name == result['currency_code']:
#             price = float(result['price'])
#         else:
#             quote_currency = self.env['res.currency'].search([('name', '=', result['currency_code'])], limit=1)
#             price = quote_currency._convert(
#                 float(result['price']), currency_order, company, order.date_order or fields.Date.today())
#
#         package_labels = []
#         for track_number, label_binary_data in result.get('label_binary_data'):
#             package_labels = package_labels + [(track_number, label_binary_data)]
#
#         carrier_tracking_ref = "+".join([pl[0] for pl in package_labels])
#         logmessage = _("Return label generated<br/>"
#                         "<b>Tracking Numbers:</b> %s<br/>"
#                         "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join([p.name for p in packages if p.name]))
#         if self.ups_label_file_type != 'GIF':
#             attachments = [('%s-%s-%s.%s' % (self.get_return_label_prefix(), pl[0], index, self.ups_label_file_type), pl[1]) for index, pl in enumerate(package_labels)]
#         else:
#             attachments = [('%s-%s-%s.%s' % (self.get_return_label_prefix(), package_labels[0][0], 1, 'pdf'), pdf.merge_pdf([pl[1] for pl in package_labels]))]
#         picking.message_post(body=logmessage, attachments=attachments)
#         shipping_data = {
#             'exact_price': price,
#             'tracking_number': carrier_tracking_ref}
#         res = res + [shipping_data]
#         return res

