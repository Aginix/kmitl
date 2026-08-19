from odoo import models


class AdvancePaymentReturnLine(models.Model):
    _inherit = "advance.payment.return.line"

    def _prepare_return_payment_vals(self):
        """Charge the inbound (return) payment to the agreement's dimensions."""
        vals = super()._prepare_return_payment_vals()
        vals["analytic_distribution"] = self.agreement_id.analytic_distribution
        return vals
