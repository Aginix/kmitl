# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    asset_count = fields.Integer(
        string="Assets",
        compute="_compute_asset_count",
    )

    def _compute_asset_count(self):
        for po in self:
            po.asset_count = self.env['account.asset.batch'].search_count([
                ('purchase_id', '=', po.id)
            ])

    def action_open_asset_batch(self):
        return {
            "name": "Asset Registration Batches",
            "type": "ir.actions.act_window",
            "res_model": "account.asset.batch",
            "view_mode": "tree,form",
            "domain": [("purchase_id", "=", self.id)],
            "context": {"default_purchase_id": self.id},
        }