# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetBatchSubcomponent(models.Model):
    _name = 'account.asset.batch.subcomponent'
    _description = 'AccountAssetBatchSubcomponent'

    batch_line_id = fields.Many2one(
        'account.asset.batch.line',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(required=True)
    sequence = fields.Integer(default=1)
