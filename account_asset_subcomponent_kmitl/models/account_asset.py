# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    subcomponent_ids = fields.One2many(
        "account.asset.subcomponent",
        "asset_id",
        string="Subcomponents",
        tracking=True
    )