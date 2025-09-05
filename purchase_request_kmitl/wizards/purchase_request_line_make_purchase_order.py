# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def make_purchase_order(self):
        for item in self.item_ids:
            line = item.line_id
            if line.purchase_lines:
                raise UserError(_(
                    "The purchase request '%s' already has a Purchase Order."
                ) % line.display_name)

        return super().make_purchase_order()


class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order.item'

    keep_description = fields.Boolean(
        string="Copy descriptions to new PO",
        help="Set true if you want to keep the "
        "descriptions provided in the "
        "wizard in the new PO.",
        default=True,
    )
    keep_estimated_cost = fields.Boolean(
        string="Copy estimative cost to new PO",
        help="Set true if you want to keep the "
        "estimated cost provided in the "
        "wizard in the new PO.",
        default=True,
    )