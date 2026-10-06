# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models


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
    # Shown on the smart button. A Char for the same reason as on the payment:
    # a field that can be edited is drawn as an input, and a button is no place
    # for one.
    payment_disbursement_request_name = fields.Char(
        related="payment_id.disbursement_request_id.name",
        string="Disbursement Request Number (Payment)",
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
        """Post a disbursement payment, then reconcile it against its bill.

        The accounting office posts the payment move through the same
        account.move maker-checker as the vendor bill (Approve = post). Because
        that path does not run ``account.payment.action_post`` (where the
        deferred reconcile normally lives), the reconciliation is triggered
        here so that posting == clearing (ล้างหนี้).

        Disbursement payments are matched by searching account.payment on the
        moves being posted (no dependency on an account.move.payment_id field).
        What posting means for the request's route is the clear station's to say.
        """
        dr_payments = self.env["account.payment"].search(
            [
                ("move_id", "in", self.ids),
                ("disbursement_request_id", "!=", False),
            ]
        )
        res = super()._post(soft=soft)
        if dr_payments:
            # Deferred reconcile now runs on the move-posting path (clearing).
            dr_payments._reconcile_source_invoice_lines()
        return res
