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

    @api.depends("state", "advance_payment_id")
    def _compute_show_create_advance_payment_button(self):
        """Borrowing money (ยืมเงิน) is a discretionary action taken after the
        request is approved — it is no longer pre-declared via a payment type."""
        for rec in self:
            rec.show_create_advance_payment_button = (
                rec.state == "approved"
                and rec.owner_id.user_id == self.env.user
                and not rec.advance_payment_id
            )

    @api.depends(
        "state",
        "advance_payment_id",
        "advance_payment_id.state",
        "has_active_disbursement",
    )
    def _compute_show_create_disbursement_button(self):
        for rec in self:
            if rec.advance_payment_id:
                # Borrowed money: bill only once the linked advance payment has
                # funds disbursed (in_progress).
                rec.show_create_disbursement_button = (
                    rec.state == "actual"
                    and rec.advance_payment_id.state == "in_progress"
                    and not rec.has_active_disbursement
                )
            else:
                # Direct pay: bill as soon as actuals are recorded.
                rec.show_create_disbursement_button = (
                    rec.state == "actual"
                    and not rec.has_active_disbursement
                )

    def _prepare_advance_payment_vals(self):
        self.ensure_one()
        loan_type = self.env.ref("advance_payment.loan_type_other")
        return {
            "requested_by": self.owner_id.user_id.id or self.env.user.id,
            "loan_reason": self.description or "",
            "loan_amount": self.total_amount,
            "loan_type_id": loan_type.id,
            "reference": "approval.request,%s" % self.id,
            "analytic_distribution": self.analytic_distribution,
            "approval_request_id": self.id,
        }

    def action_create_advance_payment(self):
        self.ensure_one()
        if self.state != "approved":
            raise UserError(
                _("Only approved approval requests can create advance payments.")
            )
        if self.advance_payment_id:
            raise UserError(
                _("An advance payment already exists for this approval request.")
            )

        vals = self._prepare_advance_payment_vals()
        advance_payment = self.env["advance.payment"].create(vals)
        self.advance_payment_id = advance_payment.id
        self.message_post(
            body=_(
                "สร้างสัญญายืมเงิน"
                " <a href='/web#id=%(id)s&amp;model=advance.payment'>"
                "<b>%(name)s</b></a> แล้ว"
                " จำนวน <b>%(amount)s %(currency)s</b>",
                id=advance_payment.id,
                name=advance_payment.name,
                amount=advance_payment.loan_amount,
                currency=advance_payment.currency_id.name,
            ),
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "advance.payment",
            "res_id": advance_payment.id,
            "view_mode": "form",
            "target": "current",
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
