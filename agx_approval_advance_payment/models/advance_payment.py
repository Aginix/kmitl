from odoo import _, api, fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    approval_request_count = fields.Integer(
        compute="_compute_approval_request_count",
    )

    reference = fields.Reference(
        selection_add=[("approval.request", "Approval Request")],
    )

    @api.depends("approval_request_id", "reference", "loan_type_id.reference_model")
    def _compute_reference_state(self):
        super()._compute_reference_state()
        for rec in self:
            if rec.approval_request_id:
                rec.is_reference_visible = True

    @api.depends("approval_request_id")
    def _compute_approval_request_count(self):
        for rec in self:
            rec.approval_request_count = 1 if rec.approval_request_id else 0

    def action_view_approval_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
