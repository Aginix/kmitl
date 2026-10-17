from odoo import fields, models


class BudgetTransferVerifyReturnWizard(models.TransientModel):
    _name = "budget.transfer.verify.return.wizard"
    _description = "Budget Transfer — Buddy Return for Correction"

    transfer_id = fields.Many2one(
        comodel_name="budget.transfer",
        required=True,
        ondelete="cascade",
    )
    reason = fields.Text(string="เหตุผลที่ส่งกลับแก้ไข", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.transfer_id._action_verify_return(self.reason)
        return {"type": "ir.actions.act_window_close"}
