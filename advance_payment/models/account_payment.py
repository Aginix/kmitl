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
        for rec in self.filtered("advance_payment_id"):
            if rec.advance_payment_id.state == "approved":
                rec.advance_payment_id.state = "in_progress"
        return res
