from odoo import fields, models

READONLY_STATES = {
    "in_progress": [("readonly", True)],
    "done": [("readonly", True)],
    "cancel": [("readonly", True)],
}


class KrisProject(models.Model):
    _inherit = "kris.project"

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
        states=READONLY_STATES,
    )
    extra_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Extra Payee",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
        states=READONLY_STATES,
    )
