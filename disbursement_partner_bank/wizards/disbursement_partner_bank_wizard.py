# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context


class DisbursementPartnerBankWizard(models.TransientModel):
    """A draft request's payee bank accounts, added or corrected inline.

    A requester cannot write ``res.partner.bank`` (base grants group_user read
    only), so the changes are applied here under sudo — only by someone who may
    edit this draft request, only for its own payees, never deleting an
    account. Each change is logged on the request; ``account`` already logs
    it on the payee's chatter too (created / updated with old → new values),
    authored by the acting user, sudo or not.
    """

    _name = "disbursement.partner.bank.wizard"
    _description = "Payee Bank Accounts"

    request_id = fields.Many2one(
        "disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
    )
    payee_ids = fields.Many2many(
        "res.partner",
        compute="_compute_payee_ids",
        string="Payees",
    )
    line_ids = fields.One2many(
        "disbursement.partner.bank.wizard.line",
        "wizard_id",
        string="Bank Accounts",
    )

    @api.depends("request_id")
    def _compute_payee_ids(self):
        for wizard in self:
            wizard.payee_ids = wizard.request_id.line_ids.partner_id

    def action_apply(self):
        self.ensure_one()
        # The action's default_* keys must not leak into what is created here.
        self = self.with_context(clean_context(self.env.context))
        request = self.request_id
        if request.state != "draft":
            raise UserError(_("Bank accounts can only be managed on a draft request."))
        request.check_access_rights("write")
        request.check_access_rule("write")
        payees = request.line_ids.partner_id
        Bank = self.env["res.partner.bank"].sudo()
        log = []
        for row in self.line_ids:
            if row.partner_id not in payees:
                raise UserError(
                    _("%s is not a payee of this request.") % row.partner_id.display_name
                )
            # Edited under sudo: the account must be this payee's own.
            owner = row.bank_account_id.sudo().partner_id
            if row.bank_account_id and owner != row.partner_id:
                raise UserError(
                    _("%s is not a bank account of this payee.")
                    % row.bank_account_id.display_name
                )
            if not row.bank_account_id and not row.bank_id:
                raise UserError(_("Choose the bank of the new account %s.") % row.acc_number)
            vals = {
                "bank_id": row.bank_id.id,
                "acc_number": row.acc_number,
                "acc_holder_name": row.acc_holder_name,
            }
            bank = row.bank_account_id.sudo()
            if bank:
                changed = {
                    k: v
                    for k, v in vals.items()
                    if (bank[k].id if k == "bank_id" else bank[k] or False) != (v or False)
                }
                if not changed:
                    continue
                bank.write(changed)
                log.append(_("edited %s") % bank.display_name)
            else:
                bank = Bank.create(
                    dict(
                        vals,
                        partner_id=row.partner_id.id,
                        company_id=request.company_id.id,
                    )
                )
                log.append(_("added %s") % bank.display_name)
            log[-1] = "%s: %s" % (row.partner_id.display_name, log[-1])
            # A line still without an account picks the one just entered.
            request.line_ids.filtered(
                lambda line, p=row.partner_id: line.partner_id == p
                and not line.partner_bank_id
            ).write({"partner_bank_id": bank.id})
        if log:
            request.message_post(
                body=Markup("%s<ul>%s</ul>")
                % (
                    _("Payee bank accounts changed:"),
                    Markup("").join(Markup("<li>%s</li>") % entry for entry in log),
                ),
                subtype_xmlid="mail.mt_note",
            )
        return {"type": "ir.actions.act_window_close"}


class DisbursementPartnerBankWizardLine(models.TransientModel):
    _name = "disbursement.partner.bank.wizard.line"
    _description = "Payee Bank Account"

    wizard_id = fields.Many2one(
        "disbursement.partner.bank.wizard",
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one("res.partner", string="Payee", required=True)
    # The account the row edits; empty on a row the user adds.
    bank_account_id = fields.Many2one("res.partner.bank", string="Bank Account")
    # Required on a new account only: an existing one may lack it.
    bank_id = fields.Many2one("res.bank", string="Bank")
    acc_number = fields.Char(string="Account Number", required=True)
    acc_holder_name = fields.Char(string="Account Holder Name")
