from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        ondelete="set null",
        index=True,
        copy=False,
        tracking=True,
    )

    reference = fields.Reference(
        selection_add=[('approval.request', 'Approval Request')],
        ondelete={'approval.request': 'set null'},
    )

    def action_view_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            raise UserError(
                _("No Approval Request linked to this request.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Approval Request"),
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
