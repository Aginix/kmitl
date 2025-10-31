# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BudgetCommitment(models.Model):
    _inherit = 'budget.commitment'

    is_budget_manager = fields.Boolean(
        compute='_compute_is_budget_user',
    )

    @api.depends_context("uid")
    def _compute_is_budget_user(self):
        user_manager_group = self.env.user.has_group(
            "budget.group_budget_manager"
        )
        for rec in self:
            rec.is_budget_manager = user_manager_group
