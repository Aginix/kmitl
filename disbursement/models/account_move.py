# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals or "payment_state" in vals:
            pipeline_states = (
                "waiting_bill_post",
                "bill_posted",
                "waiting_payment_post",
                "payment_posted",
            )
            disbursements = self.env["disbursement.request"].search(
                [
                    ("bill_id", "in", self.ids),
                    ("state", "in", pipeline_states),
                ]
            )
            if disbursements:
                disbursements._update_state_from_pipeline()
        return res
