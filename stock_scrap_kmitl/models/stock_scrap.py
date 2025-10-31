# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    reason = fields.Text(
        string="Reason",
        states={'done': [('readonly', True)]}
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Created By',
        readonly=True,
        default=lambda self: self.env.user,
        states={'done': [('readonly', True)]}
    )

    origin = fields.Char(
        states={'done': [('readonly', True)]}
    )