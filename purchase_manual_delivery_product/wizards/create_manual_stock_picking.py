# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CreateManualStockPicking(models.TransientModel):
    _inherit = 'create.stock.picking.wizard'

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'line_ids' in res:
            res['line_ids'] = []
        
        return res

    def create_stock_picking(self):
        StockPicking = self.env["stock.picking"]

        # If a picking has been selected, we add products to the picking
        # otherwise we create a new picking
        picking_id = self.picking_id
        if not picking_id:
            res = self._prepare_picking()
            picking_id = StockPicking.create(res)

        moves = self.line_ids._create_stock_moves(picking_id)
        moves = moves.filtered(
            lambda x: x.state not in ("done", "cancel")
        )._action_confirm()
        seq = 0
        for move in sorted(moves, key=lambda move: move.date_deadline or move.date):
            seq += 5
            move.sequence = seq
        moves._action_assign()
        picking_id.message_post_with_view(
            "mail.message_origin_link",
            values={"self": picking_id, "origin": self.purchase_id},
            subtype_id=self.env.ref("mail.mt_note").id,
        )

        purchase_order = self.purchase_id
        if picking_id and purchase_order:
            if picking_id.id not in purchase_order.picking_ids.ids:
                purchase_order.write({
                    'picking_ids': [(4, picking_id.id)]
                })
            
            if not picking_id.origin or purchase_order.name not in picking_id.origin:
                picking_id.write({
                    'origin': purchase_order.name
                })

        return {
            "name": _("Stock Picking"),
            "view_mode": "form",
            "res_model": "stock.picking",
            "view_id": self.env.ref("stock.view_picking_form").id,
            "res_id": picking_id.id,
            "type": "ir.actions.act_window",
        }
    
class CreateManualStockPickingWizardLine(models.TransientModel):
    _inherit = 'create.stock.picking.wizard.line'

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        domain="[('type', '=', 'product')]",
        related=False,
    )
    
    price_unit = fields.Float(
        readonly=False
    )

    def _prepare_stock_moves(self, picking):
        self.ensure_one()
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