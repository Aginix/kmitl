from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    department_analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="account_analytic_department_rel",
        column1="src_id",
        column2="department_id",
        string="Departments",
        domain="[('plan_id', '=', %(account_analytic_kmitl.analytic_plan_departments)d)]",
    )
