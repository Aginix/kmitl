# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class BudgetExpenseRequiredDepartment(models.Model):
    """Required Department (ส่วนงานที่ต้องทำแผน) -- a ส่วนงาน obligated to
    produce a Plan Document. The settings list that drives push-generation and
    who-must-plan tracking (ADR-0001)."""

    _name = "budget.expense.required.department"
    _description = "Expense Plan Required Department (ส่วนงานที่ต้องทำแผน)"
    _order = "department_analytic_id"
    _rec_name = "department_analytic_id"

    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="ส่วนงาน",
        required=True,
        domain="[('root_plan_id.code', '=', 'departments')]",
    )
    note = fields.Char(string="หมายเหตุ")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "unique_department_company",
            "unique(department_analytic_id, company_id)",
            "ส่วนงานนี้ถูกกำหนดให้ต้องทำแผนอยู่แล้ว",
        ),
    ]
