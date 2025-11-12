# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("loan", "Loan"), ("prepaid", "Prepaid")],
        tracking=True,
        string="Payment Type",
    )
