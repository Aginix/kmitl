# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BudgetAppropriationCompilation(models.Model):
    _inherit = "budget.appropriation.compilation"

    procurement_plan_line_ids = fields.One2many(
        "budget.appropriation.line",
        compute="_compute_procurement_plan_line_ids",
        store=False,
        readonly=True,
    )

    @api.depends(
        "expense_appropriation_ids.line_ids.enable_procurement_plan",
        "expense_appropriation_ids.line_ids.procurement_plan_amount",
        "expense_appropriation_ids.line_ids.procurement_plan_unit",
        "expense_appropriation_ids.line_ids.procurement_plan_id",
    )
    def _compute_procurement_plan_line_ids(self):
        for rec in self:
            rec.procurement_plan_line_ids = rec.expense_appropriation_ids.line_ids.filtered(
                lambda l: l.enable_procurement_plan
            )
