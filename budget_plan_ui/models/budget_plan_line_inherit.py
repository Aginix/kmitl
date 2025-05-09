import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class BudgetPlanLineInherit(models.Model):
    _inherit = "budget.plan.line"

    note = fields.Text()

    procurement_plan_ids = fields.One2many(
        "procurement.plan",
        "budget_plan_line_id",
        string="Procurement Plans",
    )
