# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def write(self, vals):
        res = super().write(vals)
        if "to_reconcile_payment_line_ids" in vals or "state" in vals:
            self._update_related_disbursements()
        return res

    def _update_related_disbursements(self):
        """Find and update disbursement requests linked via bills."""
        bill_ids = set()
        for payment in self:
            if payment.to_reconcile_payment_line_ids:
                bill_ids.update(
                    payment.to_reconcile_payment_line_ids.mapped("move_id").ids
                )
            bill_ids.update(payment.reconciled_bill_ids.ids)
        if bill_ids:
            pipeline_states = (
                "bill_draft",
                "bill_posted",
                "payment_draft",
                "payment_posted",
            )
            disbursements = self.env["disbursement.request"].search(
                [
                    ("bill_ids", "in", list(bill_ids)),
                    ("state", "in", pipeline_states),
                ]
            )
            if disbursements:
                disbursements._update_state_from_pipeline()
