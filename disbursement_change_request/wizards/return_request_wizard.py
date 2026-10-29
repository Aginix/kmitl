# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementReturnRequestWizard(models.TransientModel):
    _inherit = "disbursement.return.request.wizard"

    reason = fields.Text(required=False)
    outstanding_requests = fields.Text(
        string="ข้อแก้ไขที่ค้างอยู่",
        compute="_compute_outstanding_requests",
    )

    @api.depends("request_id")
    def _compute_outstanding_requests(self):
        for wizard in self:
            wizard.outstanding_requests = (
                "\n".join(wizard.request_id._outstanding_change_request_lines())
                if wizard.request_id
                else False
            )

    def action_return(self):
        """No reason needed while Change requests are outstanding."""
        self.ensure_one()
        if (self.reason or "").strip() or not self.outstanding_requests:
            return super().action_return()
        self.request_id._action_return_for_edit(self.reason)
        return {"type": "ir.actions.act_window_close"}
