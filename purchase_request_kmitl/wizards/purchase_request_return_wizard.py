from odoo import fields, models


class PurchaseRequestReturnWizard(models.TransientModel):
    _name = "purchase.request.return.wizard"
    _description = "Purchase Request Return Wizard"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        required=True,
        readonly=True,
    )
    reason = fields.Text(string="เหตุผลการตีกลับ", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.request_id._action_do_return_to_draft(self.reason)
        return {"type": "ir.actions.act_window_close"}
