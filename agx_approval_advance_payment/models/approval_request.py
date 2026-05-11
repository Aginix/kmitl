from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Advance Payment",
        readonly=True,
        copy=False,
    )

    advance_payment_count = fields.Integer(
        compute="_compute_advance_payment_count",
    )

    show_create_advance_payment_button = fields.Boolean(
        compute="_compute_show_create_advance_payment_button",
    )

    show_create_disbursement_button = fields.Boolean(
        compute="_compute_show_create_disbursement_button",
    )

    @api.depends("advance_payment_id")
    def _compute_advance_payment_count(self):
        for rec in self:
            rec.advance_payment_count = 1 if rec.advance_payment_id else 0

    @api.depends("state", "payment_type", "advance_payment_id")
    def _compute_show_create_advance_payment_button(self):
        for rec in self:
            rec.show_create_advance_payment_button = (
                rec.state == "approved"
                and rec.payment_type == "advance"
                and not rec.advance_payment_id
            )

    @api.depends(
        "state",
        "payment_type",
        "advance_payment_id",
        "advance_payment_id.state",
    )
    def _compute_show_create_disbursement_button(self):
        for rec in self:
            if rec.payment_type == "advance":
                # Show "Create Bill" only when the linked advance payment
                # has funds disbursed (in_progress state)
                rec.show_create_disbursement_button = (
                    rec.state == "approved"
                    and bool(rec.advance_payment_id)
                    and rec.advance_payment_id.state == "in_progress"
                )
            else:
                rec.show_create_disbursement_button = rec.state == "approved"

    def _prepare_advance_payment_context(self):
        self.ensure_one()
        return {
            "default_requested_by": self.owner_id.id,
            "default_department_id": self.department_id.id,
            "default_loan_reason": self.description or "",
            "default_loan_amount": self.total_amount,
            "default_approval_request_id": self.id,
            "default_reference": "approval.request,%s" % self.id,
        }

    def action_create_advance_payment(self):
        self.ensure_one()
        if self.state != "approved":
            raise UserError(
                _("Only approved approval requests can create advance payments.")
            )
        if self.payment_type != "advance":
            raise UserError(
                _("Payment type must be 'Advance' to create an advance payment.")
            )
        if self.advance_payment_id:
            raise UserError(
                _("An advance payment already exists for this approval request.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Advance Payment"),
            "res_model": "advance.payment",
            "view_mode": "form",
            "target": "current",
            "context": self._prepare_advance_payment_context(),
        }

    def action_view_advance_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "advance.payment",
            "res_id": self.advance_payment_id.id,
            "view_mode": "form",
            "target": "current",
        }
