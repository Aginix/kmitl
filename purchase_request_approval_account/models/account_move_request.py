# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveRequest(models.Model):
    _inherit = 'account.move.request'

    purchase_request_approval_id = fields.Many2one(
        comodel_name="purchase.request.approval",
        string="Purchase Order",
        ondelete="set null",
        index=True,
        tracking=True,
    )

    def action_view_purchase_approval(self):
        print("test")
