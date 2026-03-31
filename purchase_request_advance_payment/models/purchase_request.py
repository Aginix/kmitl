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

    @api.depends("advance_payment_id")
    def _compute_advance_payment_count(self):
        for rec in self:
            rec.advance_payment_count = 1 if rec.advance_payment_id else 0

    def action_create_advance_payment(self):
        """Create a draft advance payment agreement from this purchase request."""
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_("Only approved purchase requests can create advance payments."))
        if self.payment_type != "advance":
            raise UserError(_("Payment type must be 'Advance' to create an advance payment."))
        if self.advance_payment_id:
            raise UserError(_("An advance payment already exists for this purchase request."))

        loan_type = self.env.ref("advance_payment.loan_type_procurement")
        vals = {
            "requested_by": self.requested_by.id,
            "department_id": self.requested_by.employee_id.department_id.id
            if self.requested_by.employee_id
            else False,
            "reference": "purchase.request,%s" % self.id,
            "loan_amount": self.get_estimated_cost_currency(),
            "loan_type_id": loan_type.id,
            "loan_reason": self.title or self.description or "",
            "analytic_distribution": self.analytic_distribution,
        }
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
