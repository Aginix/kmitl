from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ApprovalRequestAllocation(models.Model):
    _inherit = "approval.request.allocation"

    # The Funding Loan of an `advance` (เงินยืม) row: which สัญญายืม this money
    # came out of. Chosen per row and **not** auto-matched to the recipient —
    # one participant may borrow on the group's behalf and pay the others from
    # it (ADR-0003, superseding ADR-0002's partner matching). The row is the
    # itemisation only; it never writes into the loan.
    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="สัญญายืมเงิน",
        copy=False,
        index=True,
        ondelete="restrict",
        help="สัญญายืมที่จ่ายเงินของแถวนี้ออกมา — เลือกจากสัญญาที่ผูกกับใบขออนุมัตินี้ "
        "และไม่จำเป็นต้องเป็นสัญญาของผู้รับเงินเอง",
    )

    @api.onchange("payment_type")
    def _onchange_payment_type_clear_loan(self):
        """Drop the Funding Loan when the row stops being เงินยืม."""
        if self.payment_type != "advance":
            self.advance_payment_id = False

    @api.constrains("advance_payment_id", "payment_type")
    def _check_funding_loan(self):
        for rec in self:
            loan = rec.advance_payment_id
            if not loan:
                continue
            if rec.payment_type != "advance":
                raise ValidationError(
                    _("Only a เงินยืม row may name a สัญญายืมเงิน.")
                )
            if loan.approval_request_id != rec.request_id:
                raise ValidationError(
                    _(
                        "%(loan)s is not drawn against %(request)s.",
                        loan=loan.display_name,
                        request=rec.request_id.display_name,
                    )
                )
            if loan.state == "cancel":
                raise ValidationError(
                    _(
                        "%(loan)s is cancelled and cannot fund an expense.",
                        loan=loan.display_name,
                    )
                )
