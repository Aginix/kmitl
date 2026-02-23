from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    advance_payment_id = fields.Many2one(
        "advance.payment",
        string="Advance Payment",
        copy=False,
        ondelete="set null",
    )

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        line_vals_list = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals
        )
        if not self.advance_payment_id:
            return line_vals_list
        account_id = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("advance_payment.receivable_account_id", default=0)
        )
        if account_id:
            line_vals_list[1]["account_id"] = account_id
        return line_vals_list
