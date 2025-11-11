# -*- coding: utf-8 -*-
from odoo import _, fields, models


class AccountMoveRequest(models.Model):
    _inherit = 'account.move.request'

    payment_type = fields.Selection(
        selection=[("direct", "Direct paid"), ("loan", "Loan"), ("prepaid", "Prepaid")],
        required=True,
        tracking=True,
        string="Payment Type",
        states={"submitted": [("readonly", True)], "validated": [
            ("readonly", True)], "cancel": [("readonly", True)]},
    )
