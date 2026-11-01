from odoo import fields, models


class BudgetSupportRequestVerifyReturnWizard(models.TransientModel):
    _name = "budget.support.request.verify.return.wizard"
    _description = "Budget Support Request — Buddy Return for Correction"

    request_id = fields.Many2one(
        comodel_name="budget.support.request",
        required=True,
        ondelete="cascade",
    )
    reason = fields.Text(string="เหตุผลที่ส่งกลับแก้ไข", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.request_id._action_verify_return(self.reason)
        return {"type": "ir.actions.act_window_close"}
