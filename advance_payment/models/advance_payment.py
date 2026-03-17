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
    _inherit = ["mail.thread", "mail.activity.mixin", "base.exception", "analytic.mixin"]
    _order = "main_exception_id asc, name desc, id desc"

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

    disbursement_state = fields.Selection(
        selection=[
            ("pending", "รอดำเนินการ"),
            ("paid", "จ่ายเงินแล้ว"),
        ],
        string="สถานะการจ่ายเงิน",
        readonly=True,
        copy=False,
        tracking=True,
    )

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
        domain=[("res_model", "=", "advance.payment")],
    )

    # Analytic dimension fields — computed from analytic_distribution, not stored
    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        compute="_compute_analytic_ids",
        inverse="_inverse_activity_analytic_id",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_ids",
        inverse="_inverse_department_analytic_id",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_ids",
        inverse="_inverse_fund_analytic_id",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_ids",
        inverse="_inverse_source_analytic_id",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
    )

    @api.depends("analytic_distribution")
    def _compute_analytic_ids(self):
        for rec in self:
            values = {f: False for f in self._analytic_keys.values()}
            account_ids = [int(k) for k in (rec.analytic_distribution or {})]
            for account in self.env["account.analytic.account"].browse(account_ids):
                field = self._analytic_keys.get(account.plan_id.code)
                if field:
                    values[field] = account.id
            for field, val in values.items():
                rec[field] = val

    def _inverse_activity_analytic_id(self):
        self._update_analytic_distribution("activities")

    def _inverse_department_analytic_id(self):
        self._update_analytic_distribution("departments")

    def _inverse_fund_analytic_id(self):
        self._update_analytic_distribution("funds")

    def _inverse_source_analytic_id(self):
        self._update_analytic_distribution("sources")

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

    def _prepare_account_payment_vals(self, payment_type):
        vals = {
            "partner_id": self.requested_by.partner_id.id,
            "amount": self.loan_amount,
            "currency_id": self.currency_id.id,
            "advance_payment_id": self.id,
            "analytic_distribution": self.analytic_distribution,
            "kmitl_payment_type_id": payment_type.id,
            "payment_type": payment_type.direction,
        }
        if payment_type.journal_id:
            vals["journal_id"] = payment_type.journal_id.id
        return vals

    @api.model
    def _reverse_field(self):
        return "advance_payment_ids"

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "advance_payment.action_advance_payment_exception_confirm"
        )

    @api.constrains("ignore_exception", "loan_amount", "state")
    def advance_payment_check_exception(self):
        records = self.filtered(lambda s: s.state == "submitted")
        if records:
            records._check_exception()

    def button_draft(self):
        self.write({"state": "draft"})

    def action_start(self, payment=None):
        """Transition approved agreements to in_progress (triggered by payment posting)."""
        self.write({"state": "in_progress"})
        for rec in self:
            if payment:
                body = _(
                    "Payment <a href='/web#id=%(id)s&amp;model=account.payment'><b>%(name)s</b></a>"
                    " has been confirmed. Funds of <b>%(amount)s %(currency)s</b> have been disbursed"
                    " to <b>%(partner)s</b>.",
                    id=payment.id,
                    name=payment.name,
                    amount=payment.amount,
                    currency=payment.currency_id.name,
                    partner=payment.partner_id.name,
                )
            else:
                body = _("Payment confirmed. Funds have been disbursed.")
            rec.message_post(body=body, subtype_xmlid="mail.mt_note")

    def action_submit(self):
        """Submit the agreement for approval (ส่งเพื่อขออนุมัติ)."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft agreements can be submitted."))
            if rec.detect_exceptions() and not rec.ignore_exception:
                return rec._popup_exceptions()
            if rec.name == _("New"):
                rec.name = self.env["ir.sequence"].next_by_code("advance.payment")
            rec.state = "submitted"
            rec.message_post(
                body=_(
                    "Agreement submitted for approval by <b>%(user)s</b>."
                    " Loan amount: <b>%(amount)s %(currency)s</b>.%(reason)s",
                    user=rec.requested_by.name,
                    amount=rec.loan_amount,
                    currency=rec.currency_id.name,
                    reason=_(" Reason: %(r)s", r=rec.loan_reason) if rec.loan_reason else "",
                ),
                subtype_xmlid="mail.mt_note",
            )

    def action_approve(self):
        """Approve and auto-create outbound account.payment (อนุมัติ)."""
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted agreements can be approved."))
        payment_type = self.env.ref("advance_payment.payment_type_advance_payment_outbound")
        vals_list = [rec._prepare_account_payment_vals(payment_type) for rec in self]
        payments = self.env["account.payment"].create(vals_list)
        self.write({"state": "approved", "disbursement_state": "pending"})
        payments.action_post()
        for rec, payment in zip(self, payments):
            rec.message_post(
                body=_(
                    "Agreement approved. Payment"
                    " <a href='/web#id=%(id)s&amp;model=account.payment'><b>%(name)s</b></a>"
                    " created for <b>%(amount)s %(currency)s</b> to <b>%(partner)s</b>"
                    " via journal <b>%(journal)s</b>.",
                    id=payment.id,
                    name=payment.name,
                    amount=payment.amount,
                    currency=payment.currency_id.name,
                    partner=payment.partner_id.name,
                    journal=payment.journal_id.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    def action_close(self):
        """Close the agreement (ปิดสัญญา)."""
        for rec in self:
            if rec.state != "in_progress":
                raise UserError(_("Only in-progress agreements can be closed."))
            rec.state = "done"
            rec.message_post(
                body=_(
                    "Agreement closed."
                    " Amount used: <b>%(used)s %(currency)s</b>."
                    " Amount remaining: <b>%(remaining)s %(currency)s</b>.",
                    used=rec.amount_used,
                    currency=rec.currency_id.name,
                    remaining=rec.amount_remaining,
                ),
                subtype_xmlid="mail.mt_note",
            )

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
