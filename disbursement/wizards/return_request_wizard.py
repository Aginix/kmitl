# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models


class DisbursementReturnRequestWizard(models.TransientModel):
    _name = "disbursement.return.request.wizard"
    _description = "Return Disbursement Request for Correction"

    request_id = fields.Many2one(
        "disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
    )
    reason = fields.Text(string="Reason", required=True)

    def action_return(self):
        self.ensure_one()
        self.request_id._action_return_for_edit(self.reason)
        return {"type": "ir.actions.act_window_close"}
