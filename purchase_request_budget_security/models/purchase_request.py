# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.depends("state")
    @api.depends_context("uid")
    def _compute_can_edit_budget(self):
        user_in_group = self.env.user.has_group(
            "purchase_request_security.group_purchase_request_user_all"
        )
        for rec in self:
            rec.can_edit_budget = bool(
                user_in_group and rec.state == "budget_validate"
            )
