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

    @api.onchange("loan_type_id")
    def _onchange_loan_type_id(self):
        if self.approval_request_id:
            return
        super()._onchange_loan_type_id()

    @api.depends("approval_request_id")
    def _compute_approval_request_count(self):
        for rec in self:
            rec.approval_request_count = 1 if rec.approval_request_id else 0

    def _propagate_rejection_to_reference(self):
        super()._propagate_rejection_to_reference()
        if self.approval_request_id and self.approval_request_id.state != "rejected":
            self.approval_request_id.action_cancel()
            self.approval_request_id.message_post(
                body=_(
                    "ปฏิเสธอัตโนมัติ เนื่องจากสัญญายืมเงิน"
                    " <a href='/web#id=%(id)s&amp;model=advance.payment'>"
                    "<b>%(name)s</b></a> ไม่ได้รับการอนุมัติ",
                    id=self.id,
                    name=self.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    def action_view_approval_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
