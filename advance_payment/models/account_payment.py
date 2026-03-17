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
        to_start = self.filtered(
            lambda p: p.advance_payment_id.state == "approved"
        ).mapped("advance_payment_id")
        if to_start:
            to_start.action_start()
        return res
