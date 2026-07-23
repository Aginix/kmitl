# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class BudgetExpensePlan(models.Model):
    _inherit = "budget.expense.plan"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        tracking=True,
    )


class BudgetExpensePlanAmount(models.Model):
    _inherit = "budget.expense.plan.amount"

    operating_unit_id = fields.Many2one(
        related="plan_id.operating_unit_id", store=True, string="Operating Unit"
    )
