from odoo import fields, models


class BudgetAccount(models.Model):
    _inherit = "budget.account"

    project_enabled = fields.Boolean(
        string="Enable Project/Activity",
        help="Check this to allow project/activity management for this budget account",
        tracking=True,
    )