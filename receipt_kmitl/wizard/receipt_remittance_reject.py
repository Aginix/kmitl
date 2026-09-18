# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ReceiptRemittanceReject(models.TransientModel):
    _name = "kmitl.receipt.remittance.reject"
    _description = "Reject Receipt Remittance"

    remittance_id = fields.Many2one(
        "kmitl.receipt.remittance",
        required=True,
        readonly=True,
    )
    reason = fields.Text(string="Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        remittance = self.remittance_id
        if remittance.state != "submitted":
            raise UserError(
                _("Only submitted remittances can be rejected.")
            )
        remittance.message_post(
            body=_("Remittance rejected by %s.<br/>Reason: %s")
            % (self.env.user.name, self.reason),
        )
        remittance._cancel_approver_activity()
        remittance.receipt_ids.write({"state": "draft"})
        remittance.write({"state": "draft"})
