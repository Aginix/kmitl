from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AdvancePayment(models.Model):
    """
    Advance Payment (สัญญายืมเงิน).

    Tracks the full lifecycle of employee advance payment loans:
    draft → submitted → approved → in_progress → done
    """

    _name = "advance.payment"
    _description = "Advance Payment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc, id desc"

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "approved": [("readonly", True)],
        "in_progress": [("readonly", True)],
        "done": [("readonly", True)],
    }

    name = fields.Char(
        string="Agreement Number",
        copy=False,
        tracking=True,
        default=lambda self: _("New"),
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="Requested By",
        required=True,
        default=lambda self: self.env.user,
        states=READONLY_STATES,
    )

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        default=lambda self: self.env.user.employee_id.department_id
        if self.env.user.employee_id
        else False,
        states=READONLY_STATES,
    )

    reference = fields.Reference(
        selection=[("purchase.request", "Purchase Request")],
        string="Reference",
        states=READONLY_STATES,
    )

    reference_model = fields.Char(
        compute="_compute_reference",
        store=True,
    )

    method_id = fields.Many2one(
        comodel_name="advance.payment.method",
        string="Payment Method",
        compute="_compute_method_id",
        store=True,
        readonly=False,
        states=READONLY_STATES,
    )

    loan_reason = fields.Text(
        string="Loan Reason",
        states=READONLY_STATES,
    )

    loan_type_id = fields.Many2one(
        comodel_name="advance.payment.loan.type",
        string="Loan Type",
        states=READONLY_STATES,
    )

    loan_amount = fields.Monetary(
        string="Loan Amount",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    bank_account_number = fields.Char(
        string="Bank Account Number",
        states=READONLY_STATES,
    )

    bank_id = fields.Many2one(
        comodel_name="advance.payment.bank",
        string="Bank",
        states=READONLY_STATES,
    )

    usage_line_ids = fields.One2many(
        comodel_name="advance.payment.usage.line",
        inverse_name="agreement_id",
        string="Usage Records",
        readonly=True,
    )

    amount_used = fields.Monetary(
        string="Amount Used",
        compute="_compute_amounts",
        store=True,
    )

    amount_remaining = fields.Monetary(
        string="Amount Remaining",
        compute="_compute_amounts",
        store=True,
    )

    payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="advance_payment_id",
        string="Payments",
        readonly=True,
    )

    payment_count = fields.Integer(
        compute="_compute_payment_count",
    )

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
        domain=[("res_model", "=", "advance.payment")],
    )

    @api.depends("loan_amount", "usage_line_ids.amount")
    def _compute_amounts(self):
        for rec in self:
            used = sum(rec.usage_line_ids.mapped("amount"))
            rec.amount_used = used
            rec.amount_remaining = rec.loan_amount - used

    @api.depends("payment_ids")
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    @api.depends("reference")
    def _compute_reference(self):
        for rec in self:
            rec.reference_model = rec.reference._name if rec.reference else False

    @api.depends("reference_model")
    def _compute_method_id(self):
        models_needed = {rec.reference_model for rec in self if rec.reference_model}
        method_by_model = {}
        if models_needed:
            methods = self.env["advance.payment.method"].search(
                [("default_for_model", "in", list(models_needed))]
            )
            method_by_model = {m.default_for_model: m for m in methods}
        for rec in self:
            rec.method_id = method_by_model.get(rec.reference_model, False)

    def _prepare_account_payment_vals(self, payment_type):
        vals = {
            "partner_id": self.requested_by.partner_id.id,
            "amount": self.loan_amount,
            "currency_id": self.currency_id.id,
            "advance_payment_id": self.id,
            "kmitl_payment_type_id": payment_type.id,
            "payment_type": payment_type.direction,
        }
        if payment_type.journal_id:
            vals["journal_id"] = payment_type.journal_id.id
        return vals

    def action_start(self):
        """Transition approved agreements to in_progress (triggered by payment posting)."""
        self.write({"state": "in_progress"})

    def action_submit(self):
        """Submit the agreement for approval (ส่งเพื่อขออนุมัติ)."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft agreements can be submitted."))
            if rec.name == _("New"):
                rec.name = self.env["ir.sequence"].next_by_code("advance.payment")
            rec.state = "submitted"

    def action_approve(self):
        """Approve and auto-create outbound account.payment (อนุมัติ)."""
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted agreements can be approved."))
        payment_type = self.env.ref("advance_payment.payment_type_advance_payment_outbound")
        vals_list = [rec._prepare_account_payment_vals(payment_type) for rec in self]
        self.env["account.payment"].create(vals_list)
        self.write({"state": "approved"})

    def action_close(self):
        """Close the agreement (ปิดสัญญา)."""
        for rec in self:
            if rec.state != "in_progress":
                raise UserError(_("Only in-progress agreements can be closed."))
            rec.state = "done"

    def action_view_payments(self):
        """Open linked account.payments."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_account_payments"
        )
        if self.payment_count == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.payment_ids.id
        else:
            action["domain"] = [("id", "in", self.payment_ids.ids)]
        return action

    def action_open_usage_wizard(self):
        """Open wizard to record usage of advance payment."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("บันทึกการใช้เงิน"),
            "res_model": "advance.payment.usage.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_agreement_id": self.id},
        }

    def action_open_return_wizard(self):
        """Open wizard to confirm money return."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("คืนเงิน"),
            "res_model": "advance.payment.return.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_agreement_id": self.id},
        }
