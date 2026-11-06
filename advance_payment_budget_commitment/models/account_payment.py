from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("advance_payment_id")
    def _compute_is_budget_code_required(self):
        """A loan voucher goes to the bank only with its รหัสงบประมาณ and
        core dimensions."""
        super()._compute_is_budget_code_required()
        for payment in self.filtered("advance_payment_id"):
            payment.is_budget_code_required = True
