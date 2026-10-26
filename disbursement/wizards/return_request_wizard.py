# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementReturnRequestWizard(models.TransientModel):
    _name = "disbursement.return.request.wizard"
    _description = "Send Back Disbursement Request for Correction"

    request_id = fields.Many2one(
        "disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
    )
    reason = fields.Text(string="Reason", required=True)

    def action_return(self):
        self.ensure_one()
        reason = (self.reason or "").strip()
        if not reason:
            raise UserError(_("Give a reason to send the request back."))
        self.request_id._action_return_for_edit(reason)
        return {"type": "ir.actions.act_window_close"}
