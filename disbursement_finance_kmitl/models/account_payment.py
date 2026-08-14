# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    disbursement_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Disbursement Request",
        ondelete="set null",
        index=True,
        copy=False,
    )

    def action_view_disbursement_request(self):
        """Open the ใบขอเบิก this voucher was raised for.

        A payment is one payee's slice of a request, and the request is the
        document KMITL navigates by — so every question about a voucher that is
        not about the voucher itself is answered back there.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Disbursement Request"),
            "res_model": "disbursement.request",
            "res_id": self.disbursement_request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_confirm_paid(self):
        """A voucher on a disbursement request is confirmed **on the request**.

        The one press that says the money left is given per request, standing for
        every payee it covers: a payee whose transfer went through waits for the
        payees whose did not, because a request is handed to the accounting office
        whole or not at all. Confirming a single payee here would break that and
        hand over half a request. See ADR-0005.
        """
        on_request = self.filtered("disbursement_request_id")
        if on_request:
            raise UserError(
                _(
                    "These payments are confirmed on their disbursement request, "
                    "not one by one: %s."
                )
                % ", ".join(
                    set(on_request.mapped("disbursement_request_id.name"))
                )
            )
        return super().action_confirm_paid()
