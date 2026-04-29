from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import str2bool


class AdvancePayment(models.Model):
    """
    Advance Payment (สัญญายืมเงิน).

    Tracks the full lifecycle of employee advance payment loans:
    draft → submitted → approved → in_progress → done
    """

    _name = "advance.payment"
    _description = "Advance Payment"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "base.exception",
        "analytic.mixin",
    ]
    _order = "main_exception_id asc, name desc, id desc"

    _PROTECTED_FIELDS = {
        "loan_amount",
        "loan_type_id",
        "loan_reason",
        "bank_id",
        "reference",
        "requested_by",
        "department_id",
    }

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "approved": [("readonly", True)],
        "in_progress": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
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
            ("cancel", "Cancelled"),
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

    requested_by_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="requested_by.partner_id",
        string="Requestor Partner",
        store=False,
    )

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        default=lambda self: self.env.user.employee_id.department_id,
        states=READONLY_STATES,
    )

    is_reference_visible = fields.Boolean(
        compute="_compute_reference_state",
    )

    is_locked_by_reference = fields.Boolean(
        compute="_compute_reference_state",
    )

    reference = fields.Reference(
        selection=[("purchase.request", "Purchase Request")],
        string="Reference",
        states=READONLY_STATES,
    )

    @api.depends("reference", "loan_type_id.reference_model")
    def _compute_reference_state(self):
        allow = str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("advance_payment.allow_manual_reference", default=False)
        )
        for rec in self:
            has_ref_model = bool(rec.loan_type_id.reference_model)
            rec.is_reference_visible = has_ref_model or allow
            rec.is_locked_by_reference = bool(rec.reference)

    @api.onchange("loan_type_id")
    def _onchange_loan_type_id(self):
        if self.loan_type_id and not self.loan_type_id.reference_model:
            self.reference = False

    @api.onchange("reference")
    def _onchange_reference(self):
        if self.reference:
            vals = self._prepare_vals_from_reference()
            if vals:
                self.update(vals)

    def _prepare_vals_from_reference(self):
        """Return dict of field values to auto-fill from the reference document.
        Override in bridge modules to provide model-specific values."""
        return {}

    loan_reason = fields.Text(
        string="Loan Reason",
        required=True,
        states=READONLY_STATES,
    )

    loan_type_id = fields.Many2one(
        comodel_name="advance.payment.loan.type",
        string="Loan Type",
        required=True,
        states=READONLY_STATES,
        domain="[('reference_model', '=', False)]",
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

    bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="บัญชีธนาคาร",
        states=READONLY_STATES,
    )

    use_attachment_bank = fields.Boolean(
        string="ประสงค์ใช้เลขบัญชีธนาคารตามเอกสารแนบ",
        states=READONLY_STATES,
    )

    book_bank = fields.Binary(
        string="Book Bank",
        attachment=True,
        states=READONLY_STATES,
    )
    book_bank_filename = fields.Char()

    usage_line_ids = fields.One2many(
        comodel_name="advance.payment.usage.line",
        inverse_name="agreement_id",
        string="Usage Records",
        readonly=True,
        copy=False,
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
        copy=False,
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

    date_submitted = fields.Datetime(string="Date Submitted", readonly=True, copy=False)
    date_approved = fields.Datetime(string="Date Approved", readonly=True, copy=False)
    date_closed = fields.Datetime(string="Date Closed", readonly=True, copy=False)

    cancel_reason = fields.Text(string="Reason", readonly=True, copy=False)

    return_line_ids = fields.One2many(
        comodel_name="advance.payment.return.line",
        inverse_name="agreement_id",
        string="Return Lines",
        copy=False,
    )

    amount_returned = fields.Monetary(
        string="Amount Returned",
        compute="_compute_amounts",
        store=True,
    )

    return_count = fields.Integer(
        compute="_compute_return_count",
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

    @api.onchange("requested_by")
    def _onchange_requested_by(self):
        if self.bank_id and self.bank_id.partner_id != self.requested_by.partner_id:
            self.bank_id = False
        if self.requested_by:
            self.department_id = self.requested_by.employee_id.department_id

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

    @api.depends(
        "loan_amount",
        "usage_line_ids.amount",
        "return_line_ids.amount",
        "return_line_ids.state",
    )
    def _compute_amounts(self):
        for rec in self:
            used = sum(rec.usage_line_ids.mapped("amount"))
            returned = sum(
                rec.return_line_ids.filtered(
                    lambda l: l.state in ("confirmed", "paid")
                ).mapped("amount")
            )
            rec.amount_used = used
            rec.amount_returned = returned
            rec.amount_remaining = rec.loan_amount - used - returned

    @api.depends("payment_ids")
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    @api.depends("return_line_ids")
    def _compute_return_count(self):
        for rec in self:
            rec.return_count = len(rec.return_line_ids)

    @api.constrains("loan_amount")
    def _check_loan_amount_positive(self):
        for rec in self:
            if rec.loan_amount < 0:
                raise ValidationError(_("Loan amount cannot be negative."))

    @api.constrains("name")
    def _check_name_unique(self):
        for rec in self:
            if rec.name == _("New"):
                continue
            if self.search([("name", "=", rec.name), ("id", "!=", rec.id)], limit=1):
                raise ValidationError(
                    _("Agreement number '%(name)s' must be unique!", name=rec.name)
                )

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
        if self.bank_id:
            vals["partner_bank_id"] = self.bank_id.id
        return vals

    @api.model
    def _reverse_field(self):
        return "advance_payment_ids"

    @api.model
    def _get_popup_action(self):
        return self.env.ref("advance_payment.action_advance_payment_exception_confirm")

    @api.constrains("ignore_exception", "loan_amount", "state")
    def advance_payment_check_exception(self):
        records = self.filtered(lambda s: s.state == "submitted")
        if records:
            records._check_exception()

    def write(self, vals):
        if self._PROTECTED_FIELDS & set(vals):
            non_draft = self.filtered(lambda r: r.state != "draft")
            if non_draft:
                raise UserError(_("Cannot modify a non-draft agreement."))
        return super().write(vals)

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
                    " to <b>%(partner)s</b>."
                    " ขั้นตอนถัดไป: ผู้ยืมสามารถบันทึกการใช้เงินและแจ้งคืนเงินได้",
                    id=payment.id,
                    name=payment.name,
                    amount=payment.amount,
                    currency=payment.currency_id.name,
                    partner=payment.partner_id.name,
                )
            else:
                body = _("Payment confirmed. Funds have been disbursed.")
            rec.message_post(body=body, subtype_xmlid="mail.mt_note")

    def _check_submit_permission(self):
        """Check if the current user is allowed to submit."""
        strict = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("advance_payment.strict_submit", default=False)
        )
        is_admin = self.env.user.has_group("base.group_system")
        is_manager = self.env.user.has_group(
            "advance_payment.group_advance_payment_manager"
        )
        for rec in self:
            if rec.requested_by == self.env.user or is_admin:
                continue
            if not strict and is_manager:
                continue
            raise UserError(
                _("Only the requestor or a manager can submit this agreement.")
                if not strict
                else _("Only the requestor or an admin can submit this agreement.")
            )

    def action_submit(self):
        """Submit the agreement for approval (ส่งเพื่อขออนุมัติ)."""
        self._check_submit_permission()
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft agreements can be submitted."))
            if rec.detect_exceptions() and not rec.ignore_exception:
                return rec._popup_exceptions()
            if rec.name == _("New"):
                rec.name = self.env["ir.sequence"].next_by_code("advance.payment")
            rec.date_submitted = fields.Datetime.now()
            rec.state = "submitted"
            rec.message_post(
                body=_(
                    "Agreement submitted for approval by <b>%(user)s</b>."
                    " Loan amount: <b>%(amount)s %(currency)s</b>.%(reason)s",
                    user=rec.requested_by.name,
                    amount=rec.loan_amount,
                    currency=rec.currency_id.name,
                    reason=(
                        _(" Reason: %(r)s", r=rec.loan_reason)
                        if rec.loan_reason
                        else ""
                    ),
                ),
                subtype_xmlid="mail.mt_note",
            )

    def action_approve(self):
        """Approve and auto-create outbound account.payment (อนุมัติ)."""
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted agreements can be approved."))
        payment_type = self.env.ref(
            "advance_payment.payment_type_advance_payment_outbound"
        )
        vals_list = [rec._prepare_account_payment_vals(payment_type) for rec in self]
        payments = self.env["account.payment"].create(vals_list)
        self.write(
            {
                "state": "approved",
                "disbursement_state": "pending",
                "date_approved": fields.Datetime.now(),
            }
        )
        payments.action_submit()
        for rec, payment in zip(self, payments):
            rec.message_post(
                body=_(
                    "Agreement approved. Payment"
                    " <a href='/web#id=%(id)s&amp;model=account.payment'><b>%(name)s</b></a>"
                    " created for <b>%(amount)s %(currency)s</b> to <b>%(partner)s</b>"
                    " via journal <b>%(journal)s</b>."
                    " ขั้นตอนถัดไป: รอฝ่ายการเงินดำเนินการเบิกจ่าย",
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
        """Close the agreement, or show confirmation wizard if money remains."""
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError(_("Only in-progress agreements can be closed."))
        if self.amount_remaining > 0:
            return {
                "type": "ir.actions.act_window",
                "name": _("ยืนยันการปิดสัญญา"),
                "res_model": "advance.payment.close.confirm",
                "view_mode": "form",
                "target": "new",
                "context": {"default_agreement_id": self.id},
            }
        self._do_close()

    def _do_close(self):
        """Actually close the agreement (ปิดสัญญา)."""
        for rec in self:
            if rec.state != "in_progress":
                raise UserError(_("Only in-progress agreements can be closed."))
            rec.date_closed = fields.Datetime.now()
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

    def action_reopen(self):
        """Reopen a closed agreement back to in_progress (ERP admin only)."""
        for rec in self:
            if rec.state != "done":
                raise UserError(_("Only closed agreements can be reopened."))
            rec.date_closed = False
            rec.state = "in_progress"
            rec.message_post(
                body=_(
                    "Agreement reopened by <b>%(user)s</b>.", user=self.env.user.name
                ),
                subtype_xmlid="mail.mt_note",
            )

    def action_open_cancel_wizard(self):
        """Open wizard to cancel the agreement (manager only)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ยกเลิกสัญญา"),
            "res_model": "advance.payment.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_agreement_id": self.id,
                "default_action_type": "cancel",
            },
        }

    def action_open_reject_wizard(self):
        """Open wizard to reject (return to draft) the agreement (manager only)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ส่งกลับแก้ไข"),
            "res_model": "advance.payment.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_agreement_id": self.id,
                "default_action_type": "reject",
            },
        }

    def _cancel_payments(self):
        """Reset or cancel linked outbound payments."""
        for payment in self.payment_ids.filtered(lambda p: p.state != "cancel"):
            if payment.state == "posted":
                payment.button_draft()
            elif payment.state == "submitted":
                payment.write({"state": "draft"})
            payment.button_cancel()

    def _action_do_cancel(self, reason):
        """Cancel the agreement (manager only). Voids linked payments if needed."""
        self.ensure_one()
        if self.state not in ("submitted", "approved", "in_progress"):
            raise UserError(
                _(
                    "Only submitted, approved, or in-progress agreements can be cancelled."
                )
            )
        self._cancel_payments()
        self.write(
            {
                "state": "cancel",
                "cancel_reason": reason,
                "disbursement_state": False,
            }
        )
        self.message_post(
            body=_("Agreement cancelled. Reason: %(reason)s", reason=reason),
            subtype_xmlid="mail.mt_note",
        )

    def _action_do_reject(self, reason):
        """Return the agreement to draft with a reason (manager only)."""
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(_("Only submitted agreements can be rejected."))
        self.write({"state": "draft", "cancel_reason": reason})
        self.message_post(
            body=_("Agreement returned to draft. Reason: %(reason)s", reason=reason),
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

    def action_view_return_lines(self):
        """Open linked return lines."""
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("รายการคืนเงิน"),
            "res_model": "advance.payment.return.line",
            "view_mode": "tree,form",
            "domain": [("agreement_id", "=", self.id)],
            "context": {"default_agreement_id": self.id},
        }
        if self.return_count == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.return_line_ids.id
        return action
