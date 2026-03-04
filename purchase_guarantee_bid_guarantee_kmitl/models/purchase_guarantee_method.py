# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuaranteeMethod(models.Model):
    _inherit = 'purchase.guarantee.method'

    default_for_model = fields.Selection(
        selection_add=[
            ("purchase.request", "Purchase Request"),
        ],
    )