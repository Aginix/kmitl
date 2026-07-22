from odoo import fields, models


class PurchaseRequestApprovalCancelWizard(models.TransientModel):
    _name = "purchase.request.approval.cancel.wizard"
    _description = "Purchase Request Approval Cancel Wizard"

    approval_id = fields.Many2one(
        comodel_name="purchase.request.approval",
        string="Purchase Request Approval",
        required=True,
        readonly=True,
    )
    reason = fields.Text(string="เหตุผลการยกเลิก", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.approval_id._action_do_cancel(self.reason)
        return {"type": "ir.actions.act_window_close"}
