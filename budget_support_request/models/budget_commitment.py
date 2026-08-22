from odoo import fields, models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    support_request_id = fields.Many2one(
        comodel_name="budget.support.request",
        string="Support Request",
        ondelete="set null",
        copy=False,
    )

    def action_reserve(self):
        res = super().action_reserve()
        self.mapped("support_request_id")._on_fulfilment_posted()
        return res
