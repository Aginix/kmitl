from odoo import fields, models


class AdvancePaymentLoanType(models.Model):
    """Master data for advance payment loan types (ประเภทเงินยืม)."""

    _name = "advance.payment.loan.type"
    _description = "Advance Payment Loan Type"
    _order = "name"

    name = fields.Char(string="Loan Type", required=True)
    active = fields.Boolean(default=True)
    reference_model = fields.Char(
        string="Reference Model",
        help="If set, this loan type requires a reference document of this model. "
        "Leave empty for standalone loan types.",
    )
