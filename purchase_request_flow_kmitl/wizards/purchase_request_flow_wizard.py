from odoo import fields, models


class PurchaseRequestFlowWizard(models.TransientModel):
    """One reason dialog: กลับแบบร่าง (พ.1 / พจ.1) and e-GP ถูกยกเลิก."""

    _name = "purchase.request.flow.wizard"
    _description = "Purchase Request Flow Reason"

    request_id = fields.Many2one("purchase.request", readonly=True)
    approval_id = fields.Many2one("purchase.request.approval", readonly=True)
    mode = fields.Selection(
        [
            ("recall", "กลับแบบร่าง"),
            ("egp_cancel", "e-GP ถูกยกเลิก"),
            ("pa_draft", "กลับแบบร่าง พจ.1"),
        ],
        required=True,
        readonly=True,
    )
    reason = fields.Text(string="เหตุผล", required=True)

    def action_confirm(self):
        self.ensure_one()
        if self.mode == "recall":
            self.request_id.action_flow_recall(self.reason)
        elif self.mode == "egp_cancel":
            self.request_id.action_egp_cancel(self.reason)
        else:
            self.approval_id.action_flow_to_draft(self.reason)
        return {"type": "ir.actions.act_window_close"}
