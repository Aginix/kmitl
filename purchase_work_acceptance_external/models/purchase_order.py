# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_external = fields.Boolean(
        string="Use External Inspection",
        default=False,
        tracking=True,
        copy=False,
    )