from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    budget_transfer_ids = fields.Many2many(
        comodel_name="budget.transfer",
        string="Budget Transfers",
    )
    model = fields.Selection(
        selection_add=[("budget.transfer", "Budget Transfer")],
        ondelete={"budget.transfer": "cascade"},
    )
