import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BudgetPlanLineInherit(models.Model):
    _inherit = "budget.plan.line"

    note = fields.Text()
    capital_expenditure_ids = fields.One2many(
        "capital.expenditure", "budget_plan_line_id", string="Capital Expenditure Plans"
    )
    procurement_plan_ids = fields.One2many(
        "procurement.plan",
        "budget_plan_line_id",
        string="Procurement Plans",
    )

    sum_amount = fields.Float(
        string="Total Capital Expenditure Amount",
        compute="_compute_sum_amount",
        store=True,
    )

    @api.depends("capital_expenditure_ids.amount")
    def _compute_sum_amount(self):
        for record in self:
            record.sum_amount = sum(record.capital_expenditure_ids.mapped("amount"))
