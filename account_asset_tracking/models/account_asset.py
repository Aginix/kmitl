# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    name = fields.Char(tracking=True)

    state = fields.Selection(tracking=True)

    number = fields.Char(tracking=True)

    code = fields.Char(tracking=True)

    purchase_value = fields.Monetary(tracking=True)

    salvage_value = fields.Monetary(tracking=True)

    date_start = fields.Date(tracking=True)

    profile_id = fields.Many2one(tracking=True)

    method_time = fields.Selection(tracking=True)

    method = fields.Selection(tracking=True)

    method_period = fields.Selection(tracking=True)