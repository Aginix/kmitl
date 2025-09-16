# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    snapshot_of_id = fields.Many2one(
        "purchase.order",
        string="Snapshot Of",
        help="ถ้า record นี้เป็น snapshot จะชี้ไปยัง Purchase Order ต้นฉบับ"
    )
    snapshot_ids = fields.One2many(
        "purchase.order",
        "snapshot_of_id",
        string="Snapshots",
        help="Snapshot ทั้งหมดที่สร้างจาก Purchase Order นี้"
    )
    snapshot_count = fields.Integer(
        compute="_compute_snapshot_count",
        string="Snapshot Count"
    )

    def _compute_snapshot_count(self):
        for order in self:
            order.snapshot_count = len(order.snapshot_ids)

    def action_create_snapshot(self):
        for order in self:
            snapshot = order.copy({
                "snapshot_of_id": order.id,   # เก็บ reference ว่ามาจาก PO ไหน
            })
        return True

    def action_view_snapshots(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Snapshots",
            "res_model": "purchase.order",
            "view_mode": "tree,form",
            "domain": [("snapshot_of_id", "=", self.id)],
            "context": {"default_snapshot_of_id": self.id},
        }
