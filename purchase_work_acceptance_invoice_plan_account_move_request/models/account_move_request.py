# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveRequest(models.Model):
    _inherit = 'account.move.request'

    invoice_plan_id = fields.Many2one(
        comodel_name="purchase.invoice.plan",
        string="Invoice Plan",
        help="This move request was created from a Purchase Invoice Plan.",
    )
