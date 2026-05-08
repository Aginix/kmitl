from odoo import _, fields, models


class AdvancePaymentCloseConfirm(models.TransientModel):
    _name = "advance.payment.close.confirm"
    _description = "Confirm Close Agreement"

    agreement_id = fields.Many2one(
        comodel_name="advance.payment",
        required=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="agreement_id.currency_id",
    )

    amount_remaining = fields.Monetary(
        string="Amount Remaining",
        related="agreement_id.amount_remaining",
        readonly=True,
    )

    def action_confirm(self):
        self.ensure_one()
        self.agreement_id._do_close()
        return {"type": "ir.actions.act_window_close"}
