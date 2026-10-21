# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def action_open_partner_bank_wizard(self, partners=None):
        """The bank accounts of this draft request's payees (or of
        ``partners``), editable inline: existing ones can be corrected and new
        ones added."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Bank accounts can only be managed on a draft request."))
        partners = partners or self.line_ids.partner_id
        # A requester cannot read every bank field as itself (base grants
        # group_user read only); the rows are prefilled under sudo.
        banks = partners.sudo().bank_ids.filtered(
            lambda b: not b.company_id or b.company_id == self.company_id
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Payee Bank Accounts"),
            "res_model": "disbursement.partner.bank.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.id,
                # New rows default to the payee the wizard was opened for.
                "default_partner_id": partners.id if len(partners) == 1 else False,
                "default_line_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": bank.partner_id.id,
                            "bank_account_id": bank.id,
                            "bank_id": bank.bank_id.id,
                            "acc_number": bank.acc_number,
                            "acc_holder_name": bank.acc_holder_name,
                        },
                    )
                    for bank in banks
                ],
            },
        }


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    def action_open_partner_bank_wizard(self):
        self.ensure_one()
        return self.request_id.action_open_partner_bank_wizard(self.partner_id)
