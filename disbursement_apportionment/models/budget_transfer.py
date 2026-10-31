# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    # Set on the transfer a request's apportionment posts (disbursement
    # ADR-0009): it posts with the consume act, without the review.
    disbursement_request_id = fields.Many2one(
        "disbursement.request",
        string="Apportioned by",
        readonly=True,
        copy=False,
        index=True,
    )

    def _skip_submit_review(self):
        return bool(self.disbursement_request_id) or super()._skip_submit_review()
