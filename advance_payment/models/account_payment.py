from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Advance Payment",
        ondelete="set null",
        index=True,
    )

    def action_submit(self):
        res = super().action_submit()
        for payment in self.filtered(lambda p: p.advance_payment_id.state == "approved"):
            payment.advance_payment_id.action_start(payment=payment)
        return res
