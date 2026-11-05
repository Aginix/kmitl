from odoo import models


class ProjectBudgetLine(models.Model):
    _name = "project.budget.line"
    _inherit = ["project.budget.line", "project.line.tracking.mixin"]

    _line_type_field = "budget_type"
    _line_o2m = {"income": "income_line_ids", "expense": "expense_line_ids"}
