from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectBudgetLine(models.Model):
    _inherit = "project.budget.line"

    advance_payment_line_ids = fields.One2many(
        "advance.payment.project.line", "project_line_id", string="Loan items"
    )
    borrowed_amount = fields.Float(compute="_compute_loan_amounts", compute_sudo=True)
    remaining_amount = fields.Float(compute="_compute_loan_amounts", compute_sudo=True)
    is_loan_via_pr_only = fields.Boolean(
        compute="_compute_is_loan_via_pr_only", compute_sudo=True
    )

    @api.depends(
        "amount",
        "advance_payment_line_ids.amount",
        "advance_payment_line_ids.advance_payment_id.state",
    )
    def _compute_loan_amounts(self):
        """Borrowed = the item's amount on submitted, non-cancelled loans
        (drafts do not count; closed loans do — advance_payment ADR-0033)."""
        for rec in self:
            loans = rec.advance_payment_line_ids.filtered(
                lambda line: line.advance_payment_id.state not in ("draft", "cancel")
            )
            rec.borrowed_amount = sum(loans.mapped("amount"))
            rec.remaining_amount = rec.amount - rec.borrowed_amount

    @api.depends("category_id.parent_path", "category_id.loan_via_pr_only")
    def _compute_is_loan_via_pr_only(self):
        flagged = self.env["project.budget.category"].search(
            [("loan_via_pr_only", "=", True)]
        )
        for rec in self:
            path = f"/{rec.category_id.parent_path or ''}"
            rec.is_loan_via_pr_only = any(f"/{c.id}/" in path for c in flagged)

    @api.constrains("amount")
    def _check_amount_covers_loans(self):
        for rec in self:
            if rec.remaining_amount < 0:
                raise ValidationError(
                    _("วงเงินรายการ %s ต่ำกว่ายอดที่ถูกยืมไปแล้ว", rec.name)
                )
