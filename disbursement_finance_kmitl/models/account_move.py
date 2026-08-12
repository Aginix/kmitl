# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        """Post a disbursement payment only after the bank result is confirmed,
        then reconcile it against its bill (clearing) and advance the request.

        The accounting office posts the payment move through the same
        account.move maker-checker as the vendor bill (Approve = post). Because
        that path does not run ``account.payment.action_post`` (where the
        deferred reconcile normally lives), the reconciliation is triggered
        here so that posting == clearing (ล้างหนี้), mirroring how the
        accounting bridge advances the request to ``bills_posted``.

        Disbursement payments are matched by searching account.payment on the
        moves being posted (no dependency on an account.move.payment_id field).
        """
        Payment = self.env["account.payment"]
        dr_payments = Payment.search(
            [
                ("move_id", "in", self.ids),
                ("disbursement_request_id", "!=", False),
            ]
        )
        # Guard: a voucher on a disbursement request may only post once the finance
        # office has confirmed the whole request paid. That the voucher itself is
        # paid is checked in finance_kmitl; this is the part only the request knows.
        for payment in dr_payments:
            request = payment.disbursement_request_id
            if request.state not in ("paid", "cleared"):
                raise UserError(
                    _(
                        "Payment %(payment)s cannot be posted: the disbursement "
                        "request %(dr)s is not confirmed paid by finance yet.",
                        payment=payment.name or payment.move_id.name,
                        dr=request.name,
                    )
                )

        res = super()._post(soft=soft)

        if dr_payments:
            # Deferred reconcile now runs on the move-posting path (clearing).
            dr_payments._reconcile_source_invoice_lines()
            requests = dr_payments.disbursement_request_id.filtered(
                lambda d: d.state == "paid"
            )
            for request in requests:
                active = request.payment_ids.filtered(
                    lambda p: p.state != "cancel"
                )
                if active and all(p.state == "posted" for p in active):
                    request.state = "cleared"
                    # The accounting office's work on the request is done.
                    request.activity_feedback(
                        ["disbursement_finance_kmitl.mail_activity_dr_to_book"]
                    )
        return res
