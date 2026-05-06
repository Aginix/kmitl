from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AdvancePaymentReturnLine(models.Model):
    """
    Return line for advance payment (รายการคืนเงินยืม).

    Lifecycle: draft → confirmed → pending_review → done / rejected
    """

    _name = "advance.payment.return.line"
    _description = "Advance Payment Return Line"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    agreement_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Agreement",
        required=True,
        ondelete="cascade",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="agreement_id.currency_id",
        store=True,
    )

    amount = fields.Monetary(
        string="Amount",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.today,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    note = fields.Text(
        string="Note",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Attachments",
        domain=[("res_model", "=", "advance.payment.return.line")],
    )

    payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment",
        readonly=True,
        copy=False,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("pending_review", "Pending Review"),
            ("rejected", "Rejected"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Return amount must be greater than zero."))

    def unlink(self):
        if self.filtered(lambda r: r.state in ("confirmed", "pending_review", "done")):
            raise UserError(
                _(
                    "Cannot delete return lines that are confirmed,"
                    " pending review, or done."
                )
            )
        return super().unlink()

    def _prepare_return_payment_vals(self):
        """Prepare values for creating the inbound payment."""
        self.ensure_one()
        payment_type = self.env.ref(
            "advance_payment.payment_type_advance_payment_inbound"
        )
        vals = {
            "partner_id": self.agreement_id.requested_by.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "analytic_distribution": self.agreement_id.analytic_distribution,
            "kmitl_payment_type_id": payment_type.id,
            "payment_type": payment_type.direction,
        }
        if payment_type.journal_id:
            vals["journal_id"] = payment_type.journal_id.id
        return vals

    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft return lines can be confirmed."))
            if rec.agreement_id.state != "in_progress":
                raise UserError(
                    _("Returns can only be confirmed for in-progress agreements.")
                )
            rec.write({"state": "confirmed"})

    def action_accept_review(self):
        for rec in self:
            if rec.state != "confirmed":
                raise UserError(
                    _("Only confirmed return lines can be accepted for review.")
                )
            rec.write({"state": "pending_review"})

    def action_approve(self):
        for rec in self:
            if rec.state != "pending_review":
                raise UserError(
                    _("Only pending review return lines can be approved.")
                )
            vals = rec._prepare_return_payment_vals()
            payment = self.env["account.payment"].create(vals)
            payment.action_submit()
            rec.write({"state": "done", "payment_id": payment.id})
            rec.agreement_id.message_post(
                body=_(
                    "Return of <b>%(amount)s %(currency)s</b> approved."
                    " Payment"
                    " <a href='/web#id=%(pid)s&amp;model=account.payment'>"
                    "<b>%(pname)s</b></a> created.",
                    amount=rec.amount,
                    currency=rec.currency_id.name,
                    pid=payment.id,
                    pname=payment.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    def action_reject(self):
        for rec in self:
            if rec.state != "pending_review":
                raise UserError(
                    _("Only pending review return lines can be rejected.")
                )
            rec.write({"state": "rejected"})

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state != "rejected":
                raise UserError(
                    _("Only rejected return lines can be reset to draft.")
                )
            rec.write({"state": "draft"})

    def action_admin_reset(self):
        for rec in self:
            if rec.state != "done":
                raise UserError(
                    _("Only done return lines can be reset by admin.")
                )
            if rec.payment_id:
                rec.payment_id.action_cancel()
            rec.write({"state": "draft", "payment_id": False})
