from odoo import _, fields, models


class AdvancePaymentCancelWizard(models.TransientModel):
    """Wizard to cancel or reject (return to draft) an advance payment agreement."""

    _name = "advance.payment.cancel.wizard"
    _description = "Advance Payment Cancel/Reject Wizard"

    agreement_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Agreement",
        required=True,
        readonly=True,
    )

    action_type = fields.Selection(
        selection=[
            ("cancel", "Cancel"),
            ("reject", "Reject"),
        ],
        string="Action",
        required=True,
        readonly=True,
    )

    reason = fields.Text(string="Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        if self.action_type == "cancel":
            self.agreement_id._action_do_cancel(self.reason)
        else:
            self.agreement_id._action_do_reject(self.reason)
        return {"type": "ir.actions.act_window_close"}
