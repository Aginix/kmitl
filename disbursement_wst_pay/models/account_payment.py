# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

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
