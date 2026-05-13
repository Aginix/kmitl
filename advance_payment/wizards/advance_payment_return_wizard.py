from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AdvancePaymentReturnWizard(models.TransientModel):
    """
    Wizard for employee to submit a return request (แจ้งคืนเงิน).

    Creates a return line (state=draft) with amount and proof of transfer.
    The manager then reviews and confirms the return line to create
    the inbound payment.
    """

    _name = "advance.payment.return.wizard"
    _description = "Advance Payment Return Wizard"

    agreement_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Agreement",
        required=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="agreement_id.currency_id",
    )

    loan_amount = fields.Monetary(
        string="Loan Amount",
        related="agreement_id.loan_amount",
        readonly=True,
    )

    amount_used = fields.Monetary(
        string="Amount Used",
        related="agreement_id.amount_used",
        readonly=True,
    )

    amount_returned = fields.Monetary(
        string="Amount Returned",
        related="agreement_id.amount_returned",
        readonly=True,
    )

    amount_remaining = fields.Monetary(
        string="Amount Remaining",
        related="agreement_id.amount_remaining",
        readonly=True,
    )

    amount = fields.Monetary(
        string="Return Amount",
        required=True,
    )

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="ap_return_wizard_attachment_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Proof of Transfer",
    )

    note = fields.Text(string="Note")

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Return amount must be greater than zero."))
            if rec.amount > rec.agreement_id.amount_remaining:
                raise ValidationError(
                    _(
                        "Return amount (%(amount)s) exceeds remaining balance"
                        " (%(remaining)s).",
                        amount=rec.amount,
                        remaining=rec.agreement_id.amount_remaining,
                    )
                )

    def action_confirm_return(self):
        """Create a return line (draft) for manager review."""
        self.ensure_one()
        if self.agreement_id.state != "in_progress":
            raise UserError(_("Only in-progress agreements can have a return request."))
        if not self.attachment_ids:
            raise UserError(_("Please attach proof of bank transfer before confirming."))
        line = self.env["advance.payment.return.line"].create(
            {
                "agreement_id": self.agreement_id.id,
                "amount": self.amount,
                "date": fields.Date.today(),
                "note": self.note,
            }
        )
        # Relink attachments from the wizard to the return line
        self.attachment_ids.write(
            {
                "res_model": "advance.payment.return.line",
                "res_id": line.id,
            }
        )
        note_part = _(" Note: %(note)s", note=self.note) if self.note else ""
        self.agreement_id.message_post(
            body=_(
                "Return of <b>%(amount)s %(currency)s</b> submitted by"
                " <b>%(user)s</b>.%(note)s"
                " %(count)s attachment(s) uploaded as proof.",
                amount=self.amount,
                currency=self.currency_id.name,
                user=self.env.user.name,
                note=note_part,
                count=len(self.attachment_ids),
            ),
            subtype_xmlid="mail.mt_note",
        )
        return {"type": "ir.actions.act_window_close"}
