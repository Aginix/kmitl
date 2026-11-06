from odoo import _, fields, models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    # Computed as the system: a commitment's reader may not read loans
    # (ADR-0033). The list opens under the reader's own rights.
    advance_payment_count = fields.Integer(
        string="สัญญายืมเงิน",
        compute="_compute_advance_payment_borrowed",
        compute_sudo=True,
    )
    advance_payment_borrowed_amount = fields.Monetary(
        string="ยอดยืมแล้ว",
        compute="_compute_advance_payment_borrowed",
        compute_sudo=True,
        help="ยอดยืมรวมของสัญญายืมเงินที่ส่งแล้วและยังไม่ยกเลิก",
    )
    advance_payment_headroom = fields.Monetary(
        string="วงเงินยืมคงเหลือ",
        compute="_compute_advance_payment_borrowed",
        compute_sudo=True,
        help="ยอดจองงบประมาณ หักยอดยืมแล้ว",
    )

    def _compute_advance_payment_borrowed(self):
        Loan = self.env["advance.payment"]
        for rec in self:
            rec.advance_payment_count = Loan.search_count(
                [("budget_commitment_id", "=", rec.id)]
            )
            borrowed = sum(
                Loan._get_loans_on_commitment(rec).mapped("loan_amount")
            )
            rec.advance_payment_borrowed_amount = borrowed
            rec.advance_payment_headroom = rec.amount - borrowed

    def action_view_advance_payments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("สัญญายืมเงิน"),
            "res_model": "advance.payment",
            "view_mode": "tree,form",
            "domain": [("budget_commitment_id", "=", self.id)],
            "context": {"create": False},
        }
