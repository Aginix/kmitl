from odoo import fields, models
from odoo.tools import float_compare


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # For project expenses the account is not chosen by hand — the request
    # stamps the GL account sharing the budget code (see disbursement.request »
    # _budget_account_default_account). Relaxed to required=False so a draft can be
    # saved while the account resolves; the view keeps it required for non-project
    # lines, and a blocking base.exception refuses a project code with no
    # resolvable account on submit. Attribute-only override — no compute — so it
    # merges cleanly with other budget-account-expense bridges.
    account_id = fields.Many2one(required=False)

    # The expense line of the project's Project Budget Plan this line claims
    # (ADR-0013); checked on submit by the exception rules.
    kmitl_project_budget_line_id = fields.Many2one(
        "project.budget.line",
        string="รายจ่ายของโครงการ",
        index=True,
        ondelete="restrict",
        domain="[('project_id', '=', parent.kmitl_project_id),"
        " ('budget_type', '=', 'expense')]",
    )

    def _kmitl_project_budget_line_missing(self):
        """Expense Control is on but the line names no expense line."""
        self.ensure_one()
        project = self.request_id.kmitl_project_id.sudo()
        return bool(project.expense_control and not self.kmitl_project_budget_line_id)

    def _kmitl_project_budget_line_mismatch(self):
        """The named line is not an expense line of the DR's project."""
        self.ensure_one()
        budget_line = self.kmitl_project_budget_line_id.sudo()
        return bool(budget_line) and (
            budget_line.project_id != self.request_id.kmitl_project_id
            or budget_line.budget_type != "expense"
        )

    def _kmitl_project_budget_line_exceeded(self):
        """Under Expense Control, the claims of the other submitted DRs plus
        this DR's lines on the same expense line exceed its amount. Locks the
        expense line so a concurrent submit or Project Revision waits."""
        self.ensure_one()
        budget_line = self.kmitl_project_budget_line_id.sudo()
        request = self.request_id
        if not budget_line or not request.kmitl_project_id.sudo().expense_control:
            return False
        self.env.cr.execute(
            "SELECT id FROM project_budget_line WHERE id = %s FOR UPDATE",
            (budget_line.id,),
        )
        others = self.sudo().search(
            [
                ("kmitl_project_budget_line_id", "=", budget_line.id),
                ("request_id", "!=", request.id),
                ("request_id.state", "not in", ("draft", "cancel")),
            ]
        )
        mine = request.line_ids.filtered(
            lambda line: line.kmitl_project_budget_line_id == budget_line
        )
        total = sum(others.mapped("price_total")) + sum(mine.mapped("price_total"))
        rounding = (request.currency_id or request.company_id.currency_id).rounding
        return float_compare(total, budget_line.amount, precision_rounding=rounding) > 0
