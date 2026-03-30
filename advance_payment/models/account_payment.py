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
        # Outbound: advance payment disbursement
        for payment in self.filtered(lambda p: p.advance_payment_id.state == "approved"):
            payment.advance_payment_id.write({"disbursement_state": "paid"})
            payment.advance_payment_id.action_start(payment=payment)
        # Inbound: return payment confirmation
        return_lines = self.env["advance.payment.return.line"].search(
            [("payment_id", "in", self.ids), ("state", "=", "confirmed")]
        )
        if return_lines:
            return_lines.write({"state": "paid"})
        return res
