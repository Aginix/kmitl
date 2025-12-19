# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    batch_line_id = fields.Many2one(
        "account.asset.batch.line",
        string="Asset Batch Line",
        tracking=True,
    )
    batch_id = fields.Many2one(
        "account.asset.batch",
        string="Asset Batch",
        related="batch_line_id.batch_id",
        store=True,
        readonly=True,
        tracking=True,
    )
    purchase_value = fields.Float(
        string="Purchase Value",
        compute="_compute_purchase_value",
        store=True,
        tracking=True,
    )

    @api.depends("batch_line_id", "batch_line_id.price_per_unit")
    def _compute_purchase_value(self):
        for asset in self:
            asset.purchase_value = asset.batch_line_id.price_per_unit or 0.0
