# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementPartnerBankWizard(models.TransientModel):
    """Add the missing bank account of a draft request's payees.

    A requester cannot create ``res.partner.bank`` (base grants group_user read
    only), so the accounts are created here under sudo — add only: an existing
    account is never changed or removed, and each addition is logged on the
    request for the officer who verifies it.
    """

    _name = "disbursement.partner.bank.wizard"
    _description = "Add Payee Bank Accounts"

    request_id = fields.Many2one(
        "disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
    )
    line_ids = fields.One2many(
        "disbursement.partner.bank.wizard.line",
        "wizard_id",
        string="Payees",
    )

    def action_apply(self):
        self.ensure_one()
        request = self.request_id
        if request.state != "draft":
            raise UserError(_("Bank accounts can only be added to a draft request."))
        # The accounts are created as sudo: only someone who may edit this
        # request may add them, and only for its own payees.
        request.check_access_rights("write")
        request.check_access_rule("write")
        payees = request.line_ids.partner_id
        added = []
        for row in self.line_ids:
            if row.partner_id not in payees:
                raise UserError(
                    _("%s is not a payee of this request.")
                    % row.partner_id.display_name
                )
            bank = (
                self.env["res.partner.bank"]
                .sudo()
                .create(
                    {
                        "partner_id": row.partner_id.id,
                        "bank_id": row.bank_id.id,
                        "acc_number": row.acc_number,
                        "acc_holder_name": row.acc_holder_name,
                        "company_id": request.company_id.id,
                    }
                )
            )
            request.line_ids.filtered(
                lambda l, p=row.partner_id: l.partner_id == p and not l.partner_bank_id
            ).write({"partner_bank_id": bank.id})
            added.append(
                Markup("<li>%s: %s</li>")
                % (row.partner_id.display_name, bank.sudo().display_name)
            )
        if added:
            request.message_post(
                body=Markup("%s<ul>%s</ul>")
                % (_("Bank accounts added for payees:"), Markup("").join(added)),
                subtype_xmlid="mail.mt_note",
            )
        return {"type": "ir.actions.act_window_close"}


class DisbursementPartnerBankWizardLine(models.TransientModel):
    _name = "disbursement.partner.bank.wizard.line"
    _description = "Add Payee Bank Account"

    wizard_id = fields.Many2one(
        "disbursement.partner.bank.wizard",
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Payee",
        required=True,
        readonly=True,
    )
    bank_id = fields.Many2one("res.bank", string="Bank", required=True)
    acc_number = fields.Char(string="Account Number", required=True)
    acc_holder_name = fields.Char(string="Account Holder Name")
