# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    disbursement_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Disbursement Request",
        ondelete="set null",
        index=True,
        copy=False,
    )

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals or "payment_state" in vals:
            pipeline_states = (
                "bill_draft",
                "bill_posted",
                "payment_draft",
                "payment_posted",
            )
            disbursements = self.mapped("disbursement_request_id").filtered(
                lambda d: d.state in pipeline_states
            )
            if disbursements:
                disbursements._update_state_from_pipeline()
        return res
