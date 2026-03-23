# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CreateManualStockPicking(models.TransientModel):
    _inherit = 'create.stock.picking.wizard'

    picking_type_id = fields.Many2one(
        related='purchase_id.picking_type_id',
        string="Operation Type",
        readonly=True
        )

    contract_number = fields.Char(
        related='purchase_id.contract_number',
        string="Contract Number",
        readonly=True
    )

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'line_ids' in res:
            res['line_ids'] = []

        return res

    def create_stock_picking(self):
        res = super().create_stock_picking()
        purchase_order = self.purchase_id
        picking_id = self.env['stock.picking'].browse(res['res_id'])

        if picking_id.id not in purchase_order.picking_ids.ids:
            purchase_order.write({
                'picking_ids': [(4, picking_id.id)],
            })
        return res


class CreateManualStockPickingWizardLine(models.TransientModel):
    _inherit = 'create.stock.picking.wizard.line'

    product_id = fields.Many2one(
        "product.product",
        domain="[('type', '=', 'product')]",
        related=False,
    )

    price_unit = fields.Float(
        readonly=False,
        related=False
    )

    def _compute_remaining_qty(self):
        for line in self:
            line.remaining_qty = line.qty

    def _prepare_stock_moves(self, picking):
        po_line = self.purchase_order_line_id

        if not po_line:
            return self._prepare_manual_stock_moves(picking)

        return super()._prepare_stock_moves(picking)

    def _prepare_manual_stock_moves(self, picking):
        self.ensure_one()

        location_dest_id = (
            self.wizard_id.location_dest_id.id or
            picking.location_dest_id.id
        )
        location_id = picking.location_id.id

        if not self.product_id:
            raise ValidationError(_("Product is required"))
        if self.qty <= 0:
            raise ValidationError(_("Quantity must be greater than 0"))

        values = {
            'name': self.product_id.display_name,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id or self.product_id.uom_id.id,
            'product_uom_qty': self.qty,
            'quantity_done': self.qty,
            'price_unit': self.price_unit,
            'date': fields.Datetime.now(),
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'picking_id': picking.id,
            'state': 'draft',
            'company_id': self.wizard_id.purchase_id.company_id.id,
            'picking_type_id': picking.picking_type_id.id,
            'origin': self.wizard_id.purchase_id.name,
            'route_ids': picking.picking_type_id.warehouse_id.reception_route_id,
        }

        return [values]
