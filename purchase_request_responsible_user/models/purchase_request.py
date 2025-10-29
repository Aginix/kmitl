# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        copy=False,
        default=lambda self: self.env.user,
        index=True,
    )
