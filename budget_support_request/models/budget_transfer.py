from odoo import fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    support_request_id = fields.Many2one(
        comodel_name="budget.support.request",
        string="Support Request",
        ondelete="set null",
        copy=False,
    )

    def _post_transfer(self):
        res = super()._post_transfer()
        self.mapped("support_request_id")._on_fulfilment_posted()
        return res
