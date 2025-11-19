# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    READONLY_STATES = {
        "purchase": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    contract_name = fields.Char(
        string="Contract Name",
        tracking=True,
        states=READONLY_STATES,
    )

    contract_number = fields.Char(
        string="Contract No.",
        tracking=True,
        states=READONLY_STATES,
    )
