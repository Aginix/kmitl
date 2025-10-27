# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    contract_type = fields.Selection(
        [
            ("order", "Purchase/Hire Order"),
            ("contract_buy", "Contract buy"),
            ("contract_construction", "Contract construction"),
        ],
        string="Contract type",
        tracking=True,
    )
