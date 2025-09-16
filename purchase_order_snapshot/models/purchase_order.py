# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    active = fields.Boolean(default=True)
    snapshot_count = fields.Integer(compute="_compute_snapshot_count")

    def _compute_snapshot_count(self):
        for order in self:
            order.snapshot_count = self.search_count([
            ("active", "=", False)])

    def action_create_snapshot(self):
        for order in self:
            snapshot = order.copy()
            snapshot.active = False
        return True

    def action_view_archived_orders(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Archived Purchase Orders",
            "res_model": "purchase.order",
            "view_mode": "tree,form",
            "domain": [("active", "=", False)],
            "context": {"default_active": False},
        }
