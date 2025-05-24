
from odoo.addons.delivery_ups.models.ups_request import UPSRequest
import logging 
from odoo import _, _lt
_logger = logging.getLogger(__name__)
import base64
import binascii
import io
import PIL.PdfImagePlugin   # activate PDF support in PIL
from PIL import Image
import logging
import os
import re

from zeep import Client, Plugin
from zeep.exceptions import Fault
from zeep.wsdl.utils import etree_to_string


UPS_ERROR_MAP = {
    '110002': _lt("Please provide at least one item to ship."),
    '110208': _lt("Please set a valid country in the recipient address."),
    '110308': _lt("Please set a valid country in the warehouse address."),
    '110548': _lt("A shipment cannot have a KGS/IN or LBS/CM as its unit of measurements. Configure it from the delivery method."),
    '111057': _lt("This measurement system is not valid for the selected country. Please switch from LBS/IN to KGS/CM (or vice versa). Configure it from the delivery method."),
    '111091': _lt("The selected service is not possible from your warehouse to the recipient address, please choose another service."),
    '111100': _lt("The selected service is invalid from the requested warehouse, please choose another service."),
    '111107': _lt("Please provide a valid zip code in the warehouse address."),
    '111210': _lt("The selected service is invalid to the recipient address, please choose another service."),
    '111212': _lt("Please provide a valid package type available for service and selected locations."),
    '111500': _lt("The selected service is not valid with the selected packaging."),
    '112111': _lt("Please provide a valid shipper number/Carrier Account."),
    '113020': _lt("Please provide a valid zip code in the warehouse address."),
    '113021': _lt("Please provide a valid zip code in the recipient address."),
    '120031': _lt("Exceeds Total Number of allowed pieces per World Wide Express Shipment."),
    '120100': _lt("Please provide a valid shipper number/Carrier Account."),
    '120102': _lt("Please provide a valid street in shipper's address."),
    '120105': _lt("Please provide a valid city in the shipper's address."),
    '120106': _lt("Please provide a valid state in the shipper's address."),
    '120107': _lt("Please provide a valid zip code in the shipper's address."),
    '120108': _lt("Please provide a valid country in the shipper's address."),
    '120109': _lt("Please provide a valid shipper phone number."),
    '120113': _lt("Shipper number must contain alphanumeric characters only."),
    '120114': _lt("Shipper phone extension cannot exceed the length of 4."),
    '120115': _lt("Shipper Phone must be at least 10 alphanumeric characters."),
    '120116': _lt("Shipper phone extension must contain only numbers."),
    '120122': _lt("Please provide a valid shipper Number/Carrier Account."),
    '120124': _lt("The requested service is unavailable between the selected locations."),
    '120202': _lt("Please provide a valid street in the recipient address."),
    '120205': _lt("Please provide a valid city in the recipient address."),
    '120206': _lt("Please provide a valid state in the recipient address."),
    '120207': _lt("Please provide a valid zipcode in the recipient address."),
    '120208': _lt("Please provide a valid Country in recipient's address."),
    '120209': _lt("Please provide a valid phone number for the recipient."),
    '120212': _lt("Recipient PhoneExtension cannot exceed the length of 4."),
    '120213': _lt("Recipient Phone must be at least 10 alphanumeric characters."),
    '120214': _lt("Recipient PhoneExtension must contain only numbers."),
    '120302': _lt("Please provide a valid street in the warehouse address."),
    '120305': _lt("Please provide a valid City in the warehouse address."),
    '120306': _lt("Please provide a valid State in the warehouse address."),
    '120307': _lt("Please provide a valid Zip in the warehouse address."),
    '120308': _lt("Please provide a valid Country in the warehouse address."),
    '120309': _lt("Please provide a valid warehouse Phone Number"),
    '120312': _lt("Warehouse PhoneExtension cannot exceed the length of 4."),
    '120313': _lt("Warehouse Phone must be at least 10 alphanumeric characters."),
    '120314': _lt("Warehouse Phone must contain only numbers."),
    '120412': _lt("Please provide a valid shipper Number/Carrier Account."),
    '121057': _lt("This measurement system is not valid for the selected country. Please switch from LBS/IN to KGS/CM (or vice versa). Configure it from delivery method"),
    '121210': _lt("The requested service is unavailable between the selected locations."),
    '128089': _lt("Access License number is Invalid. Provide a valid number (Length should be 0-35 alphanumeric characters)"),
    '190001': _lt("Cancel shipment not available at this time , Please try again Later."),
    '190100': _lt("Provided Tracking Ref. Number is invalid."),
    '190109': _lt("Provided Tracking Ref. Number is invalid."),
    '250001': _lt("Access License number is invalid for this provider.Please re-license."),
    '250002': _lt("Username/Password is invalid for this delivery provider."),
    '250003': _lt("Access License number is invalid for this delivery provider."),
    '250004': _lt("Username/Password is invalid for this delivery provider."),
    '250006': _lt("The maximum number of user access attempts was exceeded. So please try again later"),
    '250007': _lt("The UserId is currently locked out; please try again in 24 hours."),
    '250009': _lt("Provided Access License Number not found in the UPS database"),
    '250038': _lt("Please provide a valid shipper number/Carrier Account."),
    '250047': _lt("Access License number is revoked contact UPS to get access."),
    '250052': _lt("Authorization system is currently unavailable , try again later."),
    '250053': _lt("UPS Server Not Found"),
    '9120200': _lt("Please provide at least one item to ship")
}

class Package():
    def __init__(self, carrier, weight, quant_pack=False, name='',delivery_package=False):
        if delivery_package:
            weight = delivery_package.weight
        self.weight = carrier._ups_convert_weight(weight, carrier.ups_package_weight_unit)
        self.weight_unit = carrier.ups_package_weight_unit
        self.name = name
        self.dimension_unit = carrier.ups_package_dimension_unit
        if delivery_package:
             self.dimension = {'length': delivery_package.length, 'width': delivery_package.width, 'height': delivery_package.height}
        elif quant_pack:
            self.dimension = {'length': quant_pack.packaging_length, 'width': quant_pack.width, 'height': quant_pack.height}
        else:
            self.dimension = {'length': carrier.ups_default_package_type_id.packaging_length, 'width': carrier.ups_default_package_type_id.width, 'height': carrier.ups_default_package_type_id.height}
        self.packaging_type = quant_pack and quant_pack.shipper_package_code or False

class UPSRequest():

    def check_required_value(self, shipper, ship_from, ship_to, order=False, picking=False):
        required_field = {'city': 'City', 'country_id': 'Country', 'phone': 'Phone'}
        # Check required field for shipper
        res = [required_field[field] for field in required_field if not shipper[field]]
        if shipper.country_id.code in ('US', 'CA', 'IE') and not shipper.state_id.code:
            res.append('State')
        if not shipper.street and not shipper.street2:
            res.append('Street')
        if shipper.country_id.code != 'HK' and not shipper.zip:
            res.append('ZIP code')
        if res:
            return _("The address of your company is missing or wrong.\n(Missing field(s) : %s)", ",".join(res))
        if len(self._clean_phone_number(shipper.phone)) < 10:
            return str(UPS_ERROR_MAP.get('120115'))
        # Check required field for warehouse address
        res = [required_field[field] for field in required_field if not ship_from[field]]
        if ship_from.country_id.code in ('US', 'CA', 'IE') and not ship_from.state_id.code:
            res.append('State')
        if not ship_from.street and not ship_from.street2:
            res.append('Street')
        if ship_from.country_id.code != 'HK' and not ship_from.zip:
            res.append('ZIP code')
        if res:
            return _("The address of your warehouse is missing or wrong.\n(Missing field(s) : %s)", ",".join(res))
        if len(self._clean_phone_number(ship_from.phone)) < 10:
            return str(UPS_ERROR_MAP.get('120313'))
        # Check required field for recipient address
        res = [required_field[field] for field in required_field if field != 'phone' and not ship_to[field]]
        if ship_to.country_id.code in ('US', 'CA', 'IE') and not ship_to.state_id.code:
            res.append('State')
        if not ship_to.street and not ship_to.street2:
            res.append('Street')
        if ship_to.country_id.code != 'HK' and not ship_to.zip:
            res.append('ZIP code')
        if len(ship_to.street or '') > 35 or len(ship_to.street2 or '') > 35:
            return _("UPS address lines can only contain a maximum of 35 characters. You can split the contacts addresses on multiple lines to try to avoid this limitation.")
        if picking and not order:
            order = picking.sale_id
        phone = ship_to.mobile or ship_to.phone
        if order and not phone:
            phone = order.partner_id.mobile or order.partner_id.phone
        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            error_lines = order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type != 'service' and not line.display_type)
            if error_lines and not order.delivery_package_ids and not (picking and picking.delivery_package_ids):
                return _("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s") % ", ".join(error_lines.product_id.mapped('name'))
        if picking and not picking.delivery_package_ids:
            for ml in picking.move_line_ids.filtered(lambda ml: not ml.result_package_id and not ml.product_id.weight):
                return _("The delivery cannot be done because the weight of your product is missing.")
            packages_without_weight = picking.move_line_ids.mapped('result_package_id').filtered(lambda p: not p.shipping_weight)
            if packages_without_weight:
                return _('Packages %s do not have a positive shipping weight.', ', '.join(packages_without_weight.mapped('display_name')))
        if not phone:
            res.append('Phone')
        if res:
            return _("The recipient address is missing or wrong.\n(Missing field(s) : %s)", ",".join(res))
        if len(self._clean_phone_number(phone)) < 10:
            return str(UPS_ERROR_MAP.get('120213'))
        return False

    def process_shipment(self):
        client = self._set_client(self.ship_wsdl, 'Ship', 'ShipmentRequest')
        service = self._set_service(client, 'Ship')
        try:
            response = service.ProcessShipment(
                Request=self.request, Shipment=self.shipment,
                LabelSpecification=self.label)

            # Check if shipment is not success then return reason for that
            if response.Response.ResponseStatus.Code != "1":
                return self.get_error_message(response.Response.ResponseStatus.Code, response.Response.ResponseStatus.Description)

            result = {}
            result['label_binary_data'] = []
            for package in response.ShipmentResults.PackageResults:
                result['label_binary_data'].append((package.TrackingNumber,self.save_label(package.ShippingLabel.GraphicImage, label_file_type=self.label_file_type)))
            result['tracking_ref'] = response.ShipmentResults.ShipmentIdentificationNumber
            result['currency_code'] = response.ShipmentResults.ShipmentCharges.TotalCharges.CurrencyCode

            # Some users are qualified to receive negotiated rates
            negotiated_rate = 'NegotiatedRateCharges' in response.ShipmentResults and response.ShipmentResults.NegotiatedRateCharges and response.ShipmentResults.NegotiatedRateCharges.TotalCharge.MonetaryValue or None

            result['price'] = negotiated_rate or response.ShipmentResults.ShipmentCharges.TotalCharges.MonetaryValue
            return result

        except Fault as e:
            code = e.detail.xpath("//err:PrimaryErrorCode/err:Code", namespaces=self.ns)[0].text
            description = e.detail.xpath("//err:PrimaryErrorCode/err:Description", namespaces=self.ns)[0].text
            return self.get_error_message(code, description)
        except IOError as e:
            return self.get_error_message('0', 'UPS Server Not Found:\n%s' % e)

    
