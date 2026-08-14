# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_disbursement_request_id = fields.Many2one(
        related="payment_id.disbursement_request_id",
        string="Disbursement Request (Payment)",
        help="Which ใบขอเบิก this payment voucher's entry belongs to. The "
        "accounting office corrects the booking on the entry, not on the "
        "payment, so this is where they can get back to the request the money "
        "was paid on.",
    )

    def action_view_payment_disbursement_request(self):
        """Open the ใบขอเบิก a payment voucher's entry was made for.

        Deliberately a *related* field on the payment's own link rather than a
        second value stored on the move: ``account.move.disbursement_request_id``
        is what ``disbursement.request.bill_ids`` reads, and that One2many does
        not filter by move type — writing a request onto a payment move would put
        the voucher in the request's bill list and break everything that counts
        bills there.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Disbursement Request"),
            "res_model": "disbursement.request",
            "res_id": self.payment_disbursement_request_id.id,
            "view_mode": "form",
            "target": "current",
        }

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
