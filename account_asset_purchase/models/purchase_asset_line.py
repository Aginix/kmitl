# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseAssetLine(models.Model):
    _name = 'purchase.asset.line'
    _description = 'PurchaseAssetLine'

    name = fields.Char(
        string="Name"
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    asset_profile_id = fields.Many2one(
        comodel_name="account.asset.profile",
        string="Asset Profile",
    )