from odoo import api, fields, models


class AdvancePaymentLoanType(models.Model):
    """Master data for advance payment loan types (ประเภทเงินยืม)."""

    _name = "advance.payment.loan.type"
    _description = "Advance Payment Loan Type"
    _order = "name"

    name = fields.Char(string="Loan Type", required=True)
    active = fields.Boolean(default=True)
    reference_model = fields.Selection(
        selection="_selection_reference_model",
        string="Reference Model",
        help="If set, this loan type requires a reference document of this model. "
        "Leave empty for standalone loan types.",
    )
    # Reference filter (ADR-0023): narrows the documents the borrower is
    # offered. Evaluated server-side with the borrower's employee_id,
    # partner_id, user_id, plus uid and company_id.
    reference_domain = fields.Char(
        string="ตัวกรองเอกสารอ้างอิง",
        default="[]",
        help="Domain over the reference model. May use employee_id, partner_id"
        " and user_id (the borrower's), uid and company_id.",
    )

    @api.model
    def _selection_reference_model(self):
        """Mirror the selection of advance.payment.reference.

        Keeps master data from declaring a model the Reference field cannot
        hold — a free-text mismatch used to disable the requirement silently.
        Bridge modules that extend `reference` with `selection_add` show up
        here automatically.
        """
        return (
            self.env["advance.payment"]
            ._fields["reference"]
            ._description_selection(self.env)
        )
