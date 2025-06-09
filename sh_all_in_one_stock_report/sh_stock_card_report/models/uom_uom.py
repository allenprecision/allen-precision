# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models,_,tools
from odoo.exceptions import UserError

class Uom(models.Model):
    _inherit = 'uom.uom'

    def sh_compute_quantity(self, qty, to_unit, round=True, rounding_method='HALF-UP', raise_if_failure=True):
        """ Convert the given quantity from the current UoM `self` into a given one
            :param qty: the quantity to convert
            :param to_unit: the destination UoM record (uom.uom)
            :param raise_if_failure: only if the conversion is not possible
                - if true, raise an exception if the conversion is not possible (different UoM category),
                - otherwise, return the initial quantity
        """
        if not self or not qty:
            return qty
        self.ensure_one()

        if self != to_unit and self.category_id.id != to_unit.category_id.id:
            if raise_if_failure:
                raise UserError(_('The unit of measure %s defined on the order line doesn\'t belong to the same category as the unit of measure %s defined on the product. Please correct the unit of measure defined on the order line or on the product, they should belong to the same category.') % (self.name, to_unit.name))
            else:
                return qty

        if self == to_unit:
            amount = qty
        else:
            amount = qty / self.factor
            if to_unit:
                amount = amount * to_unit.factor
        amount = tools.float_round(amount,2,rounding_method=rounding_method)
        return amount
    