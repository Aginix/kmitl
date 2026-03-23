# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        """Propagate budget and analytic data from source invoices to payments."""
        payments = super()._create_payments()
        active_model = self._context.get("active_model")
        active_ids = self._context.get("active_ids", [])
        if active_model == "account.move" and active_ids:
            source_move = self.env["account.move"].browse(active_ids)[:1]
            vals = {}
            if source_move.analytic_distribution:
                vals["analytic_distribution"] = source_move.analytic_distribution
            if source_move.budget_commitment_id:
                vals["budget_commitment_id"] = source_move.budget_commitment_id.id
            if source_move.budget_account_id:
                vals["budget_account_id"] = source_move.budget_account_id.id
            if vals:
                for payment in payments:
                    payment.write(vals)
                    if vals.get("analytic_distribution"):
                        payment.move_id.line_ids.write(
                            {"analytic_distribution": vals["analytic_distribution"]}
                        )
        return payments

    def _post_payments(self, to_process, edit_mode=False):
        """Skip posting — payment stays in draft for user review.

        KMITL pipeline: draft → submit → bank export → tier validate → post.
        """
        return

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
