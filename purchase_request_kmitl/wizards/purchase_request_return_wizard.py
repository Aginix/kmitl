from odoo import _, fields, models


class PurchaseRequestReturnWizard(models.TransientModel):
    _name = "purchase.request.return.wizard"
    _description = "Purchase Request Return Wizard"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        required=True,
        default=lambda self: self.env.context.get("active_id"),
    )
    reason = fields.Text(string="Return Reason", required=True)

    def action_confirm_return(self):
        self.ensure_one()
        self.request_id.message_post(
            body=_("Purchase request returned. Reason: %s") % self.reason
        )
        self.request_id.button_draft()
        return {"type": "ir.actions.act_window_close"}
