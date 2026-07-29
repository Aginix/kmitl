from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    _rec_names_search = ["name", "contract_number", "approval_request_id.name"]

    # Typed mirror of `reference` when it points at an approval request. Derived
    # rather than set by hand so the two can never drift apart.
    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        compute="_compute_reference",
        store=True,
        index=True,
        ondelete="restrict",
        compute_sudo=False,
        copy=False,
    )

    approval_request_count = fields.Integer(
        compute="_compute_approval_request_count",
    )

    reference = fields.Reference(
        selection_add=[("approval.request", "Approval Request")],
    )

    @api.depends("reference")
    def _compute_reference(self):
        super()._compute_reference()
        for rec in self:
            rec.approval_request_id = (
                rec.reference if rec.reference_model == "approval.request" else False
            )

    def _check_reference_status(self):
        res = super()._check_reference_status()
        ar = self.approval_request_id
        if ar and ar.state != "approved":
            raise ValidationError(
                _(
                    "Approval request %(name)s must be approved before it can"
                    " back a loan (current status: %(state)s).",
                    name=ar.name,
                    state=dict(ar._fields["state"].selection).get(ar.state),
                )
            )
        return res

    def _prepare_vals_from_reference(self):
        """Pull the loan values off the source approval request — the mirror of
        approval.request._prepare_advance_payment_vals for the manual path."""
        vals = super()._prepare_vals_from_reference()
        ar = self.approval_request_id
        if ar:
            vals.update(
                {
                    "requested_by": ar.owner_id.user_id.id or self.env.user.id,
                    "loan_amount": ar.total_amount,
                    "loan_reason": ar.description or "",
                    "analytic_distribution": ar.analytic_distribution,
                }
            )
        return vals

    @api.depends("approval_request_id", "reference", "loan_type_id.reference_model")
    def _compute_reference_state(self):
        super()._compute_reference_state()
        for rec in self:
            if rec.approval_request_id:
                rec.is_reference_visible = True

    @api.onchange("loan_type_id")
    def _onchange_loan_type_id(self):
        """Keep an approval-request reference when the picked loan type declares
        no reference_model — AR-backed loans use loan_type_other. A type that
        requires a *different* model still clears it (handled by super)."""
        if self.approval_request_id and not self.loan_type_id.reference_model:
            return
        super()._onchange_loan_type_id()

    @api.depends("approval_request_id")
    def _compute_approval_request_count(self):
        for rec in self:
            rec.approval_request_count = 1 if rec.approval_request_id else 0

    def _action_do_cancel(self, reason):
        """Cancel the source approval request too, mirroring what
        advance_payment_disbursement does for a source purchase request."""
        res = super()._action_do_cancel(reason)
        if self.approval_request_id and self.approval_request_id.state != "rejected":
            self.approval_request_id.action_cancel()
            self.approval_request_id.message_post(
                body=_(
                    "ยกเลิกอัตโนมัติ เนื่องจากสัญญายืมเงิน"
                    " <a href='/web#id=%(id)s&amp;model=advance.payment'>"
                    "<b>%(name)s</b></a> ถูกยกเลิก",
                    id=self.id,
                    name=self.name,
                ),
                subtype_xmlid="mail.mt_note",
            )
        return res

    def action_view_approval_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
