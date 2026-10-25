from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import clean_context

from odoo.addons.base.models.res_bank import sanitize_account_number


class AdvancePaymentPartnerBankWizard(models.TransientModel):
    """Materialise a borrower's unlisted bank account (advance_payment ADR-0022).

    The borrower cannot write ``res.partner.bank`` (base grants group_user
    read only), so the loan officer checks the declared account against the
    Book Bank here and the account is created under sudo — reusing the
    borrower's own account when the number is already there.
    """

    _name = "advance.payment.partner.bank.wizard"
    _description = "Create Borrower Bank Account"

    advance_payment_id = fields.Many2one(
        "advance.payment",
        string="สัญญายืมเงิน",
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one("res.partner", string="ผู้ยืม", readonly=True)
    book_bank_file = fields.Binary(related="advance_payment_id.book_bank_file")
    book_bank_filename = fields.Char(related="advance_payment_id.book_bank_filename")
    bank_id = fields.Many2one("res.bank", string="ธนาคาร", required=True)
    acc_number = fields.Char(string="เลขที่บัญชี", required=True)
    acc_holder_name = fields.Char(string="ชื่อบัญชี")

    def action_apply(self):
        self.ensure_one()
        # The action's default_* keys must not leak into what is created here.
        self = self.with_context(clean_context(self.env.context))
        loan = self.advance_payment_id
        if not self.env.user.has_group(
            "advance_payment.group_advance_payment_loan_officer"
        ):
            raise AccessError(_("Only a loan officer can create the bank account."))
        if loan.state != "to_verify":
            raise UserError(
                _(
                    "The bank account can only be created while the request is"
                    " under verification."
                )
            )
        # The loan's own partner, not the wizard's: the account must be the
        # borrower's.
        partner = loan.partner_id
        if not partner:
            raise UserError(_("The borrower has no contact to hold the account."))
        Bank = self.env["res.partner.bank"].sudo().with_context(active_test=False)
        account = Bank.search(
            [
                ("partner_id", "=", partner.id),
                ("sanitized_acc_number", "=", sanitize_account_number(self.acc_number)),
            ],
            limit=1,
        )
        if account:
            if not account.active:
                account.active = True
            log = _("ใช้บัญชีธนาคารเดิมของผู้ยืม %s", account.display_name)
        else:
            account = Bank.create(
                {
                    "partner_id": partner.id,
                    "bank_id": self.bank_id.id,
                    "acc_number": self.acc_number,
                    "acc_holder_name": self.acc_holder_name,
                }
            )
            log = _("สร้างบัญชีธนาคาร %s ให้ผู้ยืม", account.display_name)
        loan.write({"bank_id": account.id, "use_unlisted_bank": False})
        loan.message_post(
            body=Markup("%s<br/>%s") % (log, _("โดย %s", self.env.user.name)),
            subtype_xmlid="mail.mt_note",
        )
        return {"type": "ir.actions.act_window_close"}
