# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ReceiptCancelWizard(models.TransientModel):
    _name = "receipt.kmitl.cancel.wizard"
    _description = "Receipt Cancel Wizard"

    receipt_id = fields.Many2one(
        "receipt.kmitl",
        required=True,
        readonly=True,
    )
    reason = fields.Text(required=True)

    def action_confirm(self):
        self.ensure_one()
        receipt = self.receipt_id
        if receipt.state != "issued":
            raise UserError(_("Only issued receipts can be cancelled."))
        if receipt.cash_deposit_id:
            raise UserError(
                _("This receipt is part of cash deposit %s. Use Refund instead.")
                % receipt.cash_deposit_id.display_name
            )
        receipt._apply_cancel(self.reason, self.env.user)
        return {"type": "ir.actions.act_window_close"}
