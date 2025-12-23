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
