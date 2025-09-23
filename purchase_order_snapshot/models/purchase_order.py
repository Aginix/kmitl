# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'base.snapshot']

    current_snapshot_id = fields.Many2one(
        comodel_name="purchase.order",
    )
    snapshot_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="current_snapshot_id",
        string="Old snapshots",
    )

    # ต้องการให้ copy fields ไหนใส่ในนี้
    def _get_snapshot_copy_fields(self):
        res = super()._get_snapshot_copy_fields()
        res.update({
            "partner_ref": self.partner_ref,
            "currency_id": self.currency_id.id,
        })
        return res

    def action_view_snapshots(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Snapshots",
            "res_model": "purchase.order",
            "view_mode": "tree,form",
            "domain": [("current_snapshot_id", "=", self.id), ("active", "=", False)],
        }
