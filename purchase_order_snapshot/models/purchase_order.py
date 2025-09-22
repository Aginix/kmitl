# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'base.snapshot']

    def _get_snapshot_copy_fields(self):
        res = super()._get_snapshot_copy_fields()
        res.update({
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
        })
        return res

    # def _compute_snapshot_count(self):
    #     for order in self:
    #         order.snapshot_count = len(order.snapshot_ids)

    # def action_create_snapshot(self):
    #     for order in self:
    #         snapshot = order.copy({
    #             "snapshot_of_id": order.id,   # เก็บ reference ว่ามาจาก PO ไหน
    #         })
    #     return True

    def action_view_snapshots(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Snapshots",
            "res_model": "purchase.order",
            "view_mode": "tree,form",
            # "domain": [("snapshot_of_id", "=", self.id)],
            "context": {"default_current_revision_id": self.id},
        }
