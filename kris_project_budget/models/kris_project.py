from odoo import fields, models


class KrisProject(models.Model):
    _inherit = "kris.project"

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
    extra_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Extra Payee",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
