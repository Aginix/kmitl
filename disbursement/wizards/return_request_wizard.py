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
    # "edit": return for correction (bounce to the source, or signed -> draft).
    # "verification": approver/accounting return to the verification officer.
    mode = fields.Selection(
        selection=[("edit", "Edit"), ("verification", "Verification")],
        default="edit",
    )

    def action_return(self):
        self.ensure_one()
        if self.mode == "verification":
            self.request_id._action_return_to_verification(self.reason)
        else:
            self.request_id._action_return_for_edit(self.reason)
        return {"type": "ir.actions.act_window_close"}
