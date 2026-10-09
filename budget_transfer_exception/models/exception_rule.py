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
    method = fields.Selection(
        selection_add=[
            (
                "budget_transfer_check_core_dimensions",
                "Budget Transfer: all 4 core dimensions set",
            ),
            (
                "budget_transfer_check_budget_availability",
                "Budget Transfer: sufficient budget on FROM lines",
            ),
            (
                "budget_transfer_check_both_tags",
                "Budget Transfer: at most one Pool Tag per line",
            ),
            (
                "budget_transfer_check_tag_account_mismatch",
                "Budget Transfer: Pool Tag matches the budget account type",
            ),
            (
                "budget_transfer_check_duplicate_lines",
                "Budget Transfer: no duplicate lines",
            ),
        ],
    )
