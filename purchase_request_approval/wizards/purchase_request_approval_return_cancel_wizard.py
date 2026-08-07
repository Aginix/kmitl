from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseRequestApprovalReturnCancelWizard(models.TransientModel):
    _name = "purchase.request.approval.return.cancel.wizard"
    _description = "Purchase Request Approval Return/Cancel Wizard"

    approval_id = fields.Many2one(
        comodel_name="purchase.request.approval",
        string="Purchase Request Approval",
        required=True,
        readonly=True,
    )
    mode = fields.Selection(
        [
            ("keep_number", "ส่งกลับแก้ไข (เก็บเลข พจ.1)"),
            ("new_number", "ส่งกลับแก้ไข (ไม่เก็บเลข พจ.1)"),
            ("cancel_all", "ยกเลิกเรื่อง"),
        ],
        string="การดำเนินการ",
        required=True,
        default="keep_number",
    )
    reason = fields.Text(string="เหตุผล", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.reason:
            raise UserError(_("A reason is required."))
        if self.mode == "keep_number":
            return self.approval_id._action_return_keep_number(self.reason)
        if self.mode == "new_number":
            return self.approval_id._action_return_new_number(self.reason)
        self.approval_id._action_do_cancel(self.reason)
        return {"type": "ir.actions.act_window_close"}
