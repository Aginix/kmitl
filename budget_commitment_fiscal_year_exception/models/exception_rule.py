from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    budget_commitment_ids = fields.Many2many(
        comodel_name="budget.commitment",
        string="Budget Commitments",
    )
    model = fields.Selection(
        selection_add=[("budget.commitment", "Budget Commitment")],
        ondelete={"budget.commitment": "cascade"},
    )
