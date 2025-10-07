# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_open_asset_batch(self):
        return {
            "name": "Asset Registration Batches",
            "type": "ir.actions.act_window",
            "res_model": "account.asset.batch",
            "view_mode": "tree,form",
            "domain": [("purchase_id", "=", self.id)],
            "context": {"default_purchase_id": self.id},
        }