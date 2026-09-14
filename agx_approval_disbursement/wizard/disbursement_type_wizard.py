from odoo import api, fields, models


class DisbursementTypeWizard(models.TransientModel):
    """1 ใบเบิก = 1 ประเภทการจ่ายเงิน: offers only the payment types that still
    have unbilled allocation rows, one confirm button per type. Confirming
    creates a single disbursement request of that type and opens it."""

    _name = "disbursement.type.wizard"
    _description = "Select Disbursement Payment Type"

    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        required=True,
        ondelete="cascade",
    )

    can_direct = fields.Boolean(compute="_compute_can_types")
    can_prepaid = fields.Boolean(compute="_compute_can_types")
    can_advance = fields.Boolean(compute="_compute_can_types")

    @api.depends("approval_request_id")
    def _compute_can_types(self):
        for wizard in self:
            pending = wizard.approval_request_id._pending_disbursement_payment_types()
            wizard.can_direct = "direct" in pending
            wizard.can_prepaid = "prepaid" in pending
            wizard.can_advance = "advance" in pending

    def action_confirm_direct(self):
        return self._confirm("direct")

    def action_confirm_prepaid(self):
        return self._confirm("prepaid")

    def action_confirm_advance(self):
        return self._confirm("advance")

    def _confirm(self, payment_type):
        self.ensure_one()
        disbursement = self.approval_request_id._create_disbursement_for_type(
            payment_type
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "form",
            "res_id": disbursement.id,
            "target": "current",
        }
