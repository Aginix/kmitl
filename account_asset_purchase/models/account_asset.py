# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    batch_id = fields.Many2one(
        related='batch_line_id.batch',
        tracking=True
    )

    batch_line_id = fields.Many2one(
        related='account.asset.batch.line',
        tracking=True
    )