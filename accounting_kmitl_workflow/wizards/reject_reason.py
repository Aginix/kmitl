# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveRejectReason(models.TransientModel):
    _name = "account.move.reject.reason"
    _description = "Account Move Reject Reason"

    reason = fields.Text(string="Reason", required=True)

    def action_reject(self):
        self.ensure_one()
        moves = self.env["account.move"].browse(
            self.env.context.get("active_ids", [])
        )
        moves.action_reject(self.reason)
        return {"type": "ir.actions.act_window_close"}
