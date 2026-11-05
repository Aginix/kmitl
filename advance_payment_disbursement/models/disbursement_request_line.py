from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


def _refuse_dropping_advance(lines):
    raise UserError(
        _(
            "Disbursement request lines of payment type Advance exist: "
            "they cannot be re-typed silently."
        )
    )


class DisbursementRequestLine(models.Model):
    """A line of payment type เงินยืม is a รายการชดใช้เงินยืม: it books spending
    already paid out of a loan, pays the borrower nothing, and clears its loan
    when the request's budget is consumed (ADR-0032, disbursement ADR-0009).

    The requester need not hold any loan right: the loan is read under sudo
    (picker, related display, checks).
    """

    _inherit = "disbursement.request.line"

    payment_type = fields.Selection(
        selection_add=[("advance", "Advance")],
        ondelete={"advance": _refuse_dropping_advance},
    )

    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="เลขที่สัญญายืมเงิน",
        domain="[('state', '=', 'in_progress'),"
        " ('operating_unit_id', '=', parent.operating_unit_id)]",
        index=True,
        copy=False,
        ondelete="restrict",
    )
    # Read as sudo: the requester sees the loan's figures without any right
    # on the loan.
    advance_payment_amount_remaining = fields.Monetary(
        related="advance_payment_id.amount_remaining",
        string="คงเหลือ",
        currency_field="currency_id",
    )

    def read(self, fields=None, load="_classic_read"):
        """The loan reads as in its picker: "<contract number> — <borrower>"
        (advance.payment.name_get)."""
        return super(
            DisbursementRequestLine, self.with_context(advance_payment_picker=True)
        ).read(fields=fields, load=load)

    # -------------------------------------------------------------------------
    # Payment type hooks
    # -------------------------------------------------------------------------
    def _pays_out(self):
        return self.payment_type != "advance" and super()._pays_out()

    def _requires_internal_payee(self):
        return self.payment_type == "advance" or super()._requires_internal_payee()

    def _default_taxable(self):
        return self.payment_type != "advance" and super()._default_taxable()

    def _bill_group_key(self):
        return super()._bill_group_key() + (self.advance_payment_id,)

    # -------------------------------------------------------------------------
    # The loan
    # -------------------------------------------------------------------------
    @api.onchange("payment_type")
    def _onchange_payment_type_advance_payment(self):
        if self.payment_type != "advance":
            self.advance_payment_id = False

    @api.onchange("advance_payment_id")
    def _onchange_advance_payment_id(self):
        """The borrower is the line's payee."""
        partner = self.advance_payment_id.sudo().partner_id
        if partner:
            self.partner_id = partner

    @api.constrains("payment_type", "advance_payment_id")
    def _check_advance_payment_payment_type(self):
        for line in self:
            if line.advance_payment_id and line.payment_type != "advance":
                raise ValidationError(
                    _("Only a line of payment type Advance may name a loan.")
                )

    @api.constrains("partner_id", "advance_payment_id")
    def _check_advance_payment_borrower(self):
        """A รายการชดใช้เงินยืม pays the borrower only."""
        for line in self:
            loan = line.advance_payment_id.sudo()
            if loan and line.partner_id != loan.partner_id:
                raise ValidationError(
                    _(
                        "The payee of a line clearing loan %(loan)s must be "
                        "its borrower, %(borrower)s.",
                        loan=loan.contract_number or loan.name,
                        borrower=loan.partner_id.display_name,
                    )
                )
