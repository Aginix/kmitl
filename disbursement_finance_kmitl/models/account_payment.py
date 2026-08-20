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
    # What the smart button shows. A Char and not the Many2one itself, because
    # Odoo 16 has no read mode: an editable field is always drawn as an input,
    # so putting the Many2one in the button gives it a text box to type in. Both
    # this and the id shadow the same-named fields account.move carries for the
    # *bills* of a request — a payment's link is its own, and the bill list
    # (disbursement.request.bill_ids) reads the move's.
    disbursement_request_name = fields.Char(
        related="disbursement_request_id.name",
        string="Disbursement Request Number",
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

    def _try_hand_over_requests(self, requests):
        """Ask the requests whether every voucher of theirs is accounted for now.

        ``sudo`` because the crossing is a **consequence** of what the user did, not
        something they are editing: an e-payment officer holds write on the file they
        just closed and read-only on the request it belongs to, so without it the
        close raises AccessError and rolls back — taking the file with it. The same
        reason ``_try_create_payments`` is sudo'd.
        """
        return requests.sudo()._try_hand_over_when_all_paid()

    def write(self, vals):
        """A voucher turning paid may be the one that carries its request across.

        Watched here rather than announced by whatever did the writing: a voucher
        reaches paid from an e-payment file being closed, from the finance office's
        own press, and from the request itself, and none of those should have to
        remember to tell the request.
        """
        res = super().write(vals)
        if vals.get("finance_state") == "paid":
            self._try_hand_over_requests(self.disbursement_request_id)
        return res

    def action_cancel(self):
        """A voucher can also stop holding its request back by leaving.

        Hooked on the action rather than on ``write``: ``state`` belongs to the
        journal entry through ``_inherits``, and core cancels by calling
        ``move_id.button_cancel()``, so nothing is ever written to this model.
        """
        requests = self.disbursement_request_id
        res = super().action_cancel()
        self._try_hand_over_requests(requests)
        return res

    def unlink(self):
        """A voucher removed is one fewer thing its request is waiting for."""
        requests = self.disbursement_request_id
        res = super().unlink()
        self._try_hand_over_requests(requests)
        return res

    def _hands_over_on_its_own(self):
        """A voucher on a request is handed over by the request.

        One Todo for the request rather than one per payee, for the reasons in
        ADR-0004 — so whatever marks these paid must not raise a second one.
        """
        return (
            super()
            ._hands_over_on_its_own()
            .filtered(lambda payment: not payment.disbursement_request_id)
        )

    def action_confirm_paid(self):
        """A voucher that travels in an e-payment file is confirmed by closing it.

        Not here, and not one payee at a time: closing the file is already that
        press, given for every payee the file carried, and giving it twice for one
        fact is how a request ends up half handed over.

        A voucher settled by cheque or cash is the other case. It enters no file, so
        there is nothing else to close and it is confirmed on itself — and the
        request crosses when it and its siblings are all paid (ADR-0007). Before
        this distinction existed, such a payee had no reachable press at all and its
        request sat at ``payment_authorized`` forever.
        """
        on_request = self.filtered(
            lambda payment: (
                payment.disbursement_request_id and payment.needs_bank_export
            )
        )
        if on_request:
            raise UserError(
                _(
                    "These payments go out in an e-payment file, so they are "
                    "confirmed by closing that file rather than one by one: %s."
                )
                % ", ".join(set(on_request.mapped("disbursement_request_id.name")))
            )
        return super().action_confirm_paid()
