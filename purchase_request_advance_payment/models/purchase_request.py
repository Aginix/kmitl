from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="สัญญายืมเงิน",
        readonly=True,
        copy=False,
    )

    advance_payment_count = fields.Integer(
        compute="_compute_advance_payment_count",
    )

    is_requested_by_current_user = fields.Boolean(
        compute="_compute_is_requested_by_current_user",
    )

    @api.onchange("payment_type")
    def _onchange_payment_type_advance(self):
        if self.payment_type == "advance" and self.requested_by:
            self.partner_id = self.requested_by.partner_id

    @api.depends("requested_by")
    def _compute_is_requested_by_current_user(self):
        for rec in self:
            rec.is_requested_by_current_user = rec.requested_by == self.env.user

    @api.depends("advance_payment_id")
    def _compute_advance_payment_count(self):
        for rec in self:
            rec.advance_payment_count = 1 if rec.advance_payment_id else 0

    def _prepare_advance_payment_vals(self):
        """Prepare values for creating an advance payment from this PR."""
        self.ensure_one()
        loan_type = self.env.ref("advance_payment.loan_type_procurement")
        return {
            "requested_by": self.requested_by.id,
            "reference": "purchase.request,%s" % self.id,
            "loan_amount": self.get_estimated_cost_currency(),
            "loan_type_id": loan_type.id,
            "loan_reason": self.description or "",
            "analytic_distribution": self.analytic_distribution,
            "budget_commitment_id": self.budget_commitment_id.id,
        }

    def action_create_advance_payment(self):
        """Create a draft advance payment agreement from this purchase request."""
        self.ensure_one()
        if self.payment_type != "advance":
            raise UserError(_("Payment type must be 'Advance' to create an advance payment."))
        if self.advance_payment_id:
            raise UserError(_("An advance payment already exists for this purchase request."))

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
        """Open the linked advance payment form."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "advance.payment",
            "res_id": self.advance_payment_id.id,
            "view_mode": "form",
            "target": "current",
        }
