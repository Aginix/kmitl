# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveRequest(models.Model):
    _inherit = 'account.move.request'

    payment_type = fields.Selection(
        selection=[("direct", "Direct paid"), ("loan", "Loan"), ("prepaid", "Prepaid")],
        tracking=True,
        string="Payment Type",
        states={"submitted": [("readonly", True)], "validated": [
            ("readonly", True)], "cancel": [("readonly", True)]},
    )
