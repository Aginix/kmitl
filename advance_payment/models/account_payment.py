from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Advance Payment",
        ondelete="set null",
        index=True,
    )

    def action_post(self):
        res = super().action_post()
        # Outbound advance-payment disbursement: transfer completed → the loan
        # becomes a formal debt and moves to in_progress (ADR-0001).
        for payment in self.filtered(
            lambda p: p.advance_payment_id.state == "waiting_transfer"
        ):
            payment.advance_payment_id.write({"disbursement_state": "paid"})
            payment.advance_payment_id.action_start(payment=payment)
        return res
