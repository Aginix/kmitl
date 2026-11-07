from odoo import fields, models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    account_is_procurement_plan = fields.Boolean(related="account_id.procurement_plan")
