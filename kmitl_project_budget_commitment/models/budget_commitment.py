from odoo import fields, models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    account_is_project = fields.Boolean(related="account_id.is_project")
