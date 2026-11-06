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

    def action_post(self):
        res = super().action_post()
        # Outbound advance-payment disbursement: transfer completed → the loan
        # becomes a formal debt and moves to in_progress (ADR-0001).
        # sudo: whoever posts (the accounting approver) need hold no
        # advance-payment group; posting the voucher is the authority, and
        # sudo() keeps env.uid so the chatter note still names them.
        for payment in self.sudo().filtered(
            lambda p: p.advance_payment_id.state == "approved"
        ):
            payment.advance_payment_id.action_start(payment=payment)
        return res
