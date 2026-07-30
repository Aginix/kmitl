from odoo import fields, models


class PurchaseRequestCancelWizard(models.TransientModel):
    _name = "purchase.request.cancel.wizard"
    _description = "Purchase Request Cancel Wizard"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        required=True,
        readonly=True,
    )
    reason = fields.Text(string="เหตุผลการยกเลิก", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.request_id._action_do_cancel(self.reason)
        return {"type": "ir.actions.act_window_close"}
