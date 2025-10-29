# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CreateManualStockPicking(models.TransientModel):
    _inherit = 'create.stock.picking.wizard'

    @api.model
    def default_get(self, fields):
        res = super(CreateManualStockPicking, self).default_get(fields)
        res.pop('line_ids', None)
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