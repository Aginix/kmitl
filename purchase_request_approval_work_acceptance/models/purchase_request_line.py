# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    wa_line_ids = fields.One2many(
        comodel_name="work.acceptance.line",
        inverse_name="approval_line_id",
        string="WA Lines",
        readonly=True,
    )
    qty_accepted = fields.Float(
        compute="_compute_qty_accepted",
        string="Accepted Qty.",
        store=True,
        readonly=True,
        digits="Product Unit of Measure",
    )
    qty_to_accept = fields.Float(
        compute="_compute_qty_accepted",
        string="To Accept Qty.",
        store=True,
        readonly=True,
        digits="Product Unit of Measure",
    )

    def _get_product_qty(self):
        return self.product_qty - sum(
            wa_line.product_qty
            for wa_line in self.wa_line_ids
            if wa_line.wa_id.state != "cancel"
        )

    @api.depends(
        "wa_line_ids.wa_id.state",
        "wa_line_ids.product_qty",
        "product_qty",
        "request_id.state",
    )
    def _compute_qty_accepted(self):
        for line in self:
            qty_accepted = 0.0
            for wa_line in line.wa_line_ids.filtered(
                lambda l: l.wa_id.state == "accept"
            ):
                qty_accepted += wa_line.product_uom._compute_quantity(
                    wa_line.product_qty, line.product_uom, round=False
                )
            line.qty_accepted = qty_accepted

            line.qty_to_accept = line.product_qty - qty_accepted
