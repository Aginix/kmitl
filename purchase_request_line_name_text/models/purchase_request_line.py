# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    name = fields.Text(string="Description", tracking=True)
