# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRejectWizard(models.TransientModel):
    _name = "disbursement.reject.wizard"
    _description = "Reject Disbursement Approval"

    request_id = fields.Many2one(
        "disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
    )
    reason = fields.Text(string="Reason", required=True)

    def action_reject(self):
        self.ensure_one()
        self.request_id._action_reject(self.reason)
        return {"type": "ir.actions.act_window_close"}
