# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


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
    # "edit": return for correction (bounce to the source, or signed -> draft).
    # "verification": approver/accounting return to the verification officer.
    # "head": the head returns a submitted request to the requester.
    # Each mode maps to a step on the request (see _return_step_handler).
    mode = fields.Selection(
        selection=[
            ("edit", "Edit"),
            ("verification", "Verification"),
            ("head", "Head"),
        ],
        default="edit",
    )

    def action_return(self):
        self.ensure_one()
        handler = self.request_id._return_step_handler(self.mode)
        if not handler:
            raise UserError(_("Unknown return step: %s") % self.mode)
        handler(self.reason)
        return {"type": "ir.actions.act_window_close"}
