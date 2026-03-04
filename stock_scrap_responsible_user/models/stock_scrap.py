# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Created By',
        readonly=True,
        default=lambda self: self.env.user,
        states={'done': [('readonly', True)]},
        tracking=True
    )