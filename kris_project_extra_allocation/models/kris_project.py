from odoo import fields, models


class KrisProject(models.Model):
    _inherit = "kris.project"

    extra_analytic_ids = fields.Many2many(
        "account.analytic.account",
        relation="kris_project_extra_analytic_rel",
        column1="kris_project_id",
        column2="analytic_account_id",
        string="Extra Payees",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
