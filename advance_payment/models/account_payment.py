from odoo import _, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Advance Payment",
        ondelete="set null",
        index=True,
    )

    def action_view_advance_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Advance Payment"),
            "res_model": "advance.payment",
            "view_mode": "form",
            "res_id": self.advance_payment_id.id,
            "target": "current",
        }

    def _mark_paid(self):
        res = super()._mark_paid()
        # Outbound advance-payment disbursement: the finance office confirmed
        # the money reached the borrower → the loan becomes a formal debt and
        # moves to in_progress (ADR-0034), without waiting for the posting.
        # sudo: the finance officer need hold no advance-payment group;
        # sudo() keeps env.uid so the chatter note still names them.
        for payment in self.sudo().filtered(
            lambda p: p.advance_payment_id.state == "approved"
        ):
            payment.advance_payment_id.action_start(payment=payment)
        return res

    def _unmark_paid(self):
        loans = (
            self.sudo()
            .filtered(lambda p: p.payment_type == "outbound")
            .mapped("advance_payment_id")
            .filtered(lambda loan: loan.state == "in_progress")
        )
        res = super()._unmark_paid()
        loans.action_unstart()
        return res
