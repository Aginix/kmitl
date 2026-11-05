from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, format_amount


class DisbursementRequest(models.Model):
    """Each เงินยืม line clears its own loan when the request's budget is
    consumed (ADR-0032, disbursement ADR-0009)."""

    _inherit = "disbursement.request"

    def _advance_lines(self):
        return self.line_ids.filtered(
            lambda ln: not ln.display_type and ln.payment_type == "advance"
        )

    def action_submit(self):
        for rec in self:
            if rec._advance_lines().filtered(lambda ln: not ln.advance_payment_id):
                raise UserError(
                    _(
                        "Every Advance line must name the loan "
                        "(เลขที่สัญญายืมเงิน) it clears."
                    )
                )
        return super().action_submit()

    def _check_advance_payment_clearable(self):
        """Each loan must still be owed (ค้างชำระ) and owe at least what its
        lines on this request clear."""
        self.ensure_one()
        lines = self._advance_lines()
        for loan in lines.advance_payment_id.sudo():
            amount = sum(
                lines.filtered(lambda ln: ln.advance_payment_id == loan).mapped(
                    "price_total"
                )
            )
            if loan.state != "in_progress":
                raise UserError(
                    _(
                        "Loan %(loan)s is not outstanding (ค้างชำระ): it cannot be cleared.",
                        loan=loan.contract_number or loan.name,
                    )
                )
            if (
                float_compare(
                    amount,
                    loan.amount_remaining,
                    precision_rounding=self.currency_id.rounding,
                )
                > 0
            ):
                raise UserError(
                    _(
                        "The lines clearing loan %(loan)s total %(amount)s, more "
                        "than it still owes (%(remaining)s).",
                        amount=format_amount(self.env, amount, self.currency_id),
                        loan=loan.contract_number or loan.name,
                        remaining=format_amount(
                            self.env, loan.amount_remaining, self.currency_id
                        ),
                    )
                )

    def write(self, vals):
        """ตัดงบ clears the loans. Every consume path (the consume act, the
        rector's approval, a direct claim) and a cancel end by writing
        ``budget_consumed_amount``."""
        if "budget_consumed_amount" not in vals:
            return super().write(vals)
        if vals["budget_consumed_amount"]:
            for rec in self.filtered(lambda r: not r.budget_consumed_amount):
                rec._check_advance_payment_clearable()
        res = super().write(vals)
        for rec in self:
            for loan in rec._advance_lines().advance_payment_id.sudo():
                loan._sync_cleared_amount(rec)
        return res
