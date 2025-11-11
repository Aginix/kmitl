# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveRequest(models.Model):
    _inherit = 'account.move.request'

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        ondelete="set null",
        index=True,
        tracking=True,
    )
