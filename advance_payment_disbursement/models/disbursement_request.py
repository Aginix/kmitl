from odoo import fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    # Link kept for reference only. The old DR-based clearing (auto-creating
    # advance.payment.usage.line per disbursement and driving the loan balance)
    # is dropped — the redesigned advance payment is cleared by the borrower's
    # actual_expense_amount, not by disbursement requests.
    advance_payment_id = fields.Many2one(
        "advance.payment",
        string="Advance Payment",
    )
