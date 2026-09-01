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
    reason = fields.Text(string="เหตุผล", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.reason:
            raise UserError(_("A reason is required."))
        return self.approval_id._action_return_for_revision(self.reason)
