# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class DisbursementRequest(models.Model):
    """Bridge between the Rector-delegate act and the consume-budget act: one
    press of the Rector approval does both."""

    _inherit = "disbursement.request"

    def action_approve(self):
        """The Rector-delegated approval also consumes the budget: a request
        that draws on it cannot be approved without its budget."""
        res = super().action_approve()
        for rec in self.filtered("consumes_budget"):
            rec._action_approve_budget()
            rec._disbursement_act_done("disbursement.consume_budget")
        return res
