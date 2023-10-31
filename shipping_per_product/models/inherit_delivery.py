# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# License URL : https://store.webkul.com/license.html/
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    product_temp_ids = fields.Many2many("product.template", "product_delivery_carriers", "delivery_carrier_ids", "product_temp_ids")
    is_sol_carrier = fields.Boolean("SOL Carrier")
    sol_grouping = fields.Selection([('y', 'Yes'),('n', 'No')], string="Delivery Grouping", default="y", help="By enabling this common delivery will be generated for same carriers.")
    product_specific = fields.Boolean("Available only for the linked products")
    sol_free_config = fields.Selection([('y', 'Yes'),('n', 'No')], string="Free Delivery Applied Per Product", default="n", help="By enabling this free config setting is applied per product instead per order.")

    def sol_carrier_rate_shipment(self, order, lines=None, sol_free_config=None):
        # temp_so = order.copy(default={'state':'draft'})
        inactive_sol = order.order_line
        res = {}
        if lines:
            order_amount = order._compute_amount_total_without_delivery()
            inactive_sol = inactive_sol - lines
            delivery_lines = inactive_sol.filtered(lambda l:l.is_delivery)
            inactive_sol = inactive_sol - delivery_lines
            inactive_sol.write({'active':False})
            res = self.rate_shipment(order)

            if not sol_free_config:
                # Checking free config for complete order
                if res['success'] and self.free_over and order_amount >= self.amount:
                    res['warning_message'] = _('The shipping is free since the order amount exceeds %.2f.') % (self.amount)
                    res['price'] = 0.0

            lines.write({
                'delivery_carrier_id' : self.id,
                'delivery_charge' : res["price"]/len(lines),
                'is_delivered': True
            })
            lines.write({'unique_grp_key':str(lines[0].id)})
            inactive_sol.write({'active':True})
        elif self.is_sol_carrier:
            sol_free_config = True if self.sol_free_config == 'y' else None
            order_amount = order._compute_amount_total_without_delivery()
            carrier_id = order.carrier_id
            for line in order.order_line.filtered(lambda l: l.is_delivery == False):
                line_carrier = line.delivery_carrier_id
                if line_carrier:
                    order.write({'carrier_id' : line_carrier.id})
                    inactive_sol = order.order_line - line
                    inactive_sol.write({'active':False})
                    res = line_carrier.rate_shipment(order)

                    if not sol_free_config:
                        # Checking free config for complete order
                        if res['success'] and self.free_over and order_amount >= self.amount:
                            res['warning_message'] = _('The shipping is free since the order amount exceeds %.2f.') % (self.amount)
                            res['price'] = 0.0
                    line.write({
                        'delivery_charge' : res["price"],
                        'is_delivered': True
                    })
                    inactive_sol.write({'active':True})
                else:
                    line.delivery_charge = 0.0
            shipping_cost = order.get_total_sol_delivery_price()
            res.update({
                'price': shipping_cost,
                'carrier_price': shipping_cost,
            })
            order.write({'carrier_id': carrier_id.id})
        else:
            res = self.rate_shipment(order)
            # temp_so.sudo().unlink()
            return res
        # temp_so.sudo().unlink()
        return res

    def write(self, vals):
        for rec in self:
            if vals.get('website_published',False) and rec.is_sol_carrier:
                raise UserError(_('You can not publish the dynamic delivery charges.'))
            if vals.get('active') != None and not vals.get('active') and rec.is_sol_carrier:
                raise UserError(_('You can not inactive the dynamic delivery charges.'))
        return super(DeliveryCarrier, self).write(vals)

    def unlink(self):
        sol_carriers = self.filtered('is_sol_carrier').mapped('name')
        if sol_carriers:
            raise UserError(_('You can not delete the dynamic delivery charges(s): %s.' % ", ".join(sol_carriers)))
        else:
            return super(DeliveryCarrier, self).unlink()

class StockMove(models.Model):
    _inherit = 'stock.move'

    def sol_assign_picking(self):
        Picking = self.env['stock.picking']
        for move in self:
            sol_grouping = move.sale_line_id.order_id.carrier_id.sol_grouping
            sol_grouping = True if sol_grouping == 'y' else False
            new_picking = False
            domain = [
                ('carrier_id', '=', move.sale_line_id.delivery_carrier_id.id),
                ('group_id', '=', move.group_id.id),
                ('location_id', '=', move.location_id.id),
                ('location_dest_id', '=', move.location_dest_id.id),
                ('picking_type_id', '=', move.picking_type_id.id),
                ('printed', '=', False),
                ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned']),
            ]
            if not sol_grouping:
                domain += [('unique_grp_key', '=', move.sale_line_id.unique_grp_key)]
            picking = Picking.search(domain, limit=1)
            if not picking:
                new_picking = True
                values = move._get_new_picking_values()
                values.update({
                    'carrier_id' : move.sale_line_id.delivery_carrier_id.id,
                    'unique_grp_key' : move.sale_line_id.unique_grp_key
                })
                picking = Picking.create(values)
            move.write({'picking_id': picking.id})
        return True

    def _assign_picking(self):
        sol_moves = self.env["stock.move"]
        for move in self:
            if move.sale_line_id.delivery_carrier_id and move.sale_line_id.order_id.carrier_id.is_sol_carrier:
                sol_moves += move
        without_sol_moves = self - sol_moves
        sol_moves.sol_assign_picking()
        return super(StockMove, without_sol_moves)._assign_picking()

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    unique_grp_key = fields.Char("Delivery Grouping Key")
