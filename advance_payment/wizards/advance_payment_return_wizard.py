from odoo import _, fields, models
from odoo.exceptions import UserError


class AdvancePaymentReturnWizard(models.TransientModel):
    """
    Wizard for employee to submit a return request (แจ้งคืนเงิน).

    The employee attaches proof of bank transfer and confirms. This sets
    is_return_requested=True on the agreement so the manager can review
    and manually close it. The agreement is NOT closed automatically.
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

    amount_remaining = fields.Monetary(
        string="Amount Remaining",
        related="agreement_id.amount_remaining",
        readonly=True,
    )

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="ap_return_wizard_attachment_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Proof of Transfer",
    )

    note = fields.Text(string="Note")

    def action_confirm_return(self):
        """Submit return request: attach proof and flag the agreement for manager review."""
        self.ensure_one()
        if self.agreement_id.state != "in_progress":
            raise UserError(_("Only in-progress agreements can have a return request."))
        if not self.attachment_ids:
            raise UserError(_("Please attach proof of bank transfer before confirming."))
        # Relink attachments from the wizard to the agreement record
        self.attachment_ids.write(
            {
                "res_model": "advance.payment",
                "res_id": self.agreement_id.id,
            }
        )
        note_part = _(" Note: %(note)s", note=self.note) if self.note else ""
        self.agreement_id.write({"is_return_requested": True})
        self.agreement_id.message_post(
            body=_(
                "Return requested by <b>%(user)s</b>.%(note)s"
                " %(count)s attachment(s) uploaded as proof.",
                user=self.env.user.name,
                note=note_part,
                count=len(self.attachment_ids),
            ),
            subtype_xmlid="mail.mt_note",
        )
        return {"type": "ir.actions.act_window_close"}
