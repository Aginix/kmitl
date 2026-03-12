# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _post_payments(self, to_process, edit_mode=False):
        """Submit payments instead of posting them.

        KMITL requires payments to go through an approval workflow
        (draft -> submitted -> posted) rather than being posted immediately.
        """
        payments = self.env["account.payment"]
        for vals in to_process:
            payments |= vals["payment"]
        payments.action_submit()

    def _reconcile_payments(self, to_process, edit_mode=False):
        """Defer reconciliation until the payment is posted.

        Since the payment is only submitted (not posted), its move lines
        cannot be reconciled yet. Store the source invoice lines on the
        payment so they can be reconciled when the payment is eventually
        approved and posted.
        """
        for vals in to_process:
            payment = vals["payment"]
            lines = vals["to_reconcile"]
            payment.to_reconcile_payment_line_ids = lines
