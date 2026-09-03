from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import str2bool

# Activity type of the "To Do" raised on whoever a pending state waits for —
# the loan officer at to_verify, the approver at to_approve. It is the generic
# type, so every lookup must also match the summary (ADR-0013/0015).
WORKFLOW_ACTIVITY_XMLID = "mail.mail_activity_data_todo"


class AdvancePayment(models.Model):
    """
    Advance Payment (สัญญายืมเงิน).

    A single-disbursement employee loan. Lifecycle (see docs/adr/0001-0005 and
    docs/advance-payment-lifecycle.drawio):

        draft → to_verify → to_approve → waiting_transfer → in_progress
              → to_verify_report → to_reconcile → done
        (+ negative: cancel)

    A borrower may hold only one active agreement at a time (serial borrowing).
    """

    _name = "advance.payment"
    _description = "Advance Payment"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "base.exception",
    ]
    _order = "main_exception_id asc, name desc, id desc"
    # Bridge modules append their typed source-document mirror (e.g.
    # "purchase_request_id.name") so a loan can be found by its source number.
    _rec_names_search = ["name", "contract_number"]

    # States in which a borrower is considered to "hold" an agreement, for the
    # one-active-agreement-per-borrower rule (ADR-0001).
    ACTIVE_STATES = ("to_verify", "to_approve", "waiting_transfer", "in_progress")

    # Material ("สาระสำคัญ") fields — locked once the request leaves draft.
    # A finance officer may still correct them while in to_verify (and bank_id
    # up to the transfer); an admin may always correct them. (ADR-0001/0005)
    _PROTECTED_FIELDS = {
        "loan_amount",
        "loan_type_id",
        "bank_id",
        "reference",
        "employee_id",
    }

    # Material fields are read-only in the UI in every non-draft state.
    READONLY_STATES = {
        state: [("readonly", True)]
        for state in (
            "to_verify",
            "to_approve",
            "waiting_transfer",
            "in_progress",
            "to_verify_report",
            "to_reconcile",
            "done",
            "cancel",
        )
    }

    # loan_reason stays editable by the creator through to_verify (ADR-0001).
    REASON_READONLY_STATES = {
        state: [("readonly", True)]
        for state in (
            "to_approve",
            "waiting_transfer",
            "in_progress",
            "to_verify_report",
            "to_reconcile",
            "done",
            "cancel",
        )
    }

    name = fields.Char(
        string="Agreement Number",
        copy=False,
        tracking=True,
        default=lambda self: _("New"),
    )

    contract_number = fields.Char(
        string="Contract Number",
        copy=False,
        readonly=True,
        tracking=True,
        help="Formal loan-contract number, assigned when the transfer completes "
        "(Effective Date). Distinct from the ADV running number.",
    )

    state = fields.Selection(
        selection=[
            ("draft", "แบบร่าง"),
            ("to_verify", "รอตรวจสอบคำขอ"),
            ("to_approve", "รออนุมัติ"),
            ("waiting_transfer", "รอการโอนเงิน"),
            ("in_progress", "อยู่ในระยะเวลาสัญญา"),
            ("to_verify_report", "รอตรวจรับรายงาน"),
            ("to_reconcile", "รอตรวจสอบเงินคืน"),
            ("done", "ปิดสัญญา"),
            ("cancel", "ยกเลิก"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="ผู้ยืม",
        required=True,
        default=lambda self: self.env.user.employee_id,
        states=READONLY_STATES,
        tracking=True,
    )

    # Who filled the form in — the source of truth for "ผู้จัดทำ", not create_uid,
    # so a manager can correct a mis-attributed request. Grants visibility to a
    # `user`-tier drafter via the own-only rule (ADR-0014).
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้จัดทำ",
        required=True,
        default=lambda self: self.env.uid,
        tracking=True,
    )

    # The borrower's payable partner — KMITL's employee↔partner link is
    # work_contact_id (cf. agx_approval's participant resolver), not
    # address_home_id. Stored so the bank domain and the payment vals read one
    # column instead of hopping into hr.employee (ADR-0014).
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="employee_id.work_contact_id",
        string="Requestor Partner",
        store=True,
    )

    is_reference_visible = fields.Boolean(
        compute="_compute_reference_state",
    )

    is_locked_by_reference = fields.Boolean(
        compute="_compute_reference_state",
    )

    is_requester = fields.Boolean(compute="_compute_is_requester")

    is_loan_officer = fields.Boolean(compute="_compute_is_loan_officer")

    # Mirrors _check_submit_permission: only the borrower or an admin may
    # submit — used to hide the button for a `user`-tier drafter-on-behalf,
    # who would otherwise hit a UserError on click.
    can_submit = fields.Boolean(compute="_compute_can_submit")

    # Mirrors _check_creator_only: only a `user`-tier staffer or an admin may
    # point employee_id at somebody else (ADR-0010, amended by ADR-0014).
    can_draft_on_behalf = fields.Boolean(compute="_compute_can_draft_on_behalf")

    # Mirrors _check_verify_permission: only the officer named on
    # loan_verifier_id (or an admin) may verify — not any loan-officer-group
    # member (ADR-0013).
    can_verify = fields.Boolean(compute="_compute_can_verify")

    # Mirrors _check_approve_permission: only the approver named on
    # approver_id (or an admin) may approve — not any loan-approver-group
    # member (ADR-0017).
    can_approve = fields.Boolean(compute="_compute_can_approve")

    # True only for a manager/admin — gates edit access to user_id, the
    # "ผู้จัดทำ" field, in the UI (ADR-0014).
    can_edit_drafter = fields.Boolean(compute="_compute_can_edit_drafter")

    @api.depends("employee_id")
    def _compute_is_requester(self):
        for rec in self:
            rec.is_requester = rec.employee_id.user_id == self.env.user

    @api.depends("employee_id")
    def _compute_can_submit(self):
        is_admin = self.env.user.has_group("base.group_system")
        for rec in self:
            rec.can_submit = is_admin or rec.employee_id.user_id == self.env.user

    def _is_strict_own_only(self):
        """Strict mode: a request may only ever be created for oneself — the
        `user` tier's draft-on-behalf power (ADR-0010) is switched off."""
        return str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("advance_payment.strict_own_only", default=False)
        )

    def _can_draft_on_behalf(self):
        """Single source for both the form gate and _check_creator_only."""
        if self.env.user.has_group("base.group_system"):
            return True  # escape hatch survives strict mode (ADR-0014)
        return not self._is_strict_own_only() and self.env.user.has_group(
            "advance_payment.group_advance_payment_user"
        )

    def _compute_can_draft_on_behalf(self):
        allowed = self._can_draft_on_behalf()
        for rec in self:
            rec.can_draft_on_behalf = allowed

    def _compute_can_edit_drafter(self):
        allowed = self.env.user.has_group(
            "advance_payment.group_advance_payment_manager"
        ) or self.env.user.has_group("base.group_system")
        for rec in self:
            rec.can_edit_drafter = allowed

    @api.depends("loan_verifier_id")
    def _compute_can_verify(self):
        is_admin = self.env.user.has_group("base.group_system")
        for rec in self:
            rec.can_verify = is_admin or rec.loan_verifier_id == self.env.user

    @api.depends("approver_id")
    def _compute_can_approve(self):
        is_admin = self.env.user.has_group("base.group_system")
        for rec in self:
            rec.can_approve = is_admin or rec.approver_id == self.env.user

    def _compute_is_loan_officer(self):
        is_loan_officer = self.env.user.has_group(
            "advance_payment.group_advance_payment_loan_officer"
        )
        for rec in self:
            rec.is_loan_officer = is_loan_officer

    is_manager = fields.Boolean(compute="_compute_is_manager")

    def _compute_is_manager(self):
        is_manager = self.env.user.has_group(
            "advance_payment.group_advance_payment_manager"
        )
        for rec in self:
            rec.is_manager = is_manager

    reference = fields.Reference(
        selection=[("purchase.request", "Purchase Request")],
        string="Reference",
        states=READONLY_STATES,
    )

    # Model of the source document, derived from `reference` — the counterpart
    # of the requirement declared on loan_type_id.reference_model. Stored so it
    # is searchable and usable in exception-rule domains. Bridge modules extend
    # _compute_reference to also fill their own typed Many2one mirror.
    reference_model = fields.Char(
        string="Reference Model",
        compute="_compute_reference",
        store=True,
        compute_sudo=False,
        readonly=True,
        copy=False,
    )

    @api.depends("reference")
    def _compute_reference(self):
        for rec in self:
            rec.reference_model = rec.reference._name if rec.reference else False

    def _check_reference_status(self):
        """Hook: verify the source document is in a state that may back a loan.

        Override in bridge modules and raise ValidationError when it is not.
        Only enforced while the agreement is still in draft — once submitted,
        the source document is free to move on with its own lifecycle.
        """
        self.ensure_one()
        return True

    # Deliberately NOT triggered on `state`: a reset-to-draft must not fail
    # just because the source document moved on with its own lifecycle.
    @api.constrains("reference", "loan_type_id")
    def _check_reference_matches_loan_type(self):
        for rec in self:
            required = rec.loan_type_id.reference_model
            if rec.reference and required and rec.reference._name != required:
                raise ValidationError(
                    _(
                        "Loan type '%(type)s' expects a reference of"
                        " %(expected)s, but %(actual)s was given.",
                        type=rec.loan_type_id.name,
                        expected=required,
                        actual=rec.reference._name,
                    )
                )
            if rec.reference and rec.state == "draft":
                rec._check_reference_status()

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
        """Drop a reference the newly picked loan type cannot accept — including
        when switching between two reference-backed types."""
        required = self.loan_type_id.reference_model
        if self.reference and (not required or self.reference._name != required):
            self.reference = False

    @api.onchange("reference")
    def _onchange_reference(self):
        if self.reference:
            self._apply_vals_from_reference()

    def _apply_vals_from_reference(self):
        """Validate the source document and pull its values onto the loan.

        Bridge modules that replace the `reference` widget with a typed picker
        must call this from their own onchange — otherwise picking a source
        document never prefills anything.
        """
        self._check_reference_status()
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
        states=REASON_READONLY_STATES,
    )

    loan_type_id = fields.Many2one(
        comodel_name="advance.payment.loan.type",
        string="Loan Type",
        required=True,
        states=READONLY_STATES,
    )

    # The reference model this loan type *requires* — as opposed to
    # `reference_model`, which is the model actually attached. Exposed so views
    # can swap in a model-specific picker (ADR-0007).
    loan_type_reference_model = fields.Selection(
        related="loan_type_id.reference_model",
        string="Required Reference Model",
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

    return_due_date = fields.Date(
        string="วันครบกำหนดคืน",
        copy=False,
        tracking=True,
        help="Set by the loan officer after approval; drives the weekly "
        "overdue reminders.",
    )

    @api.model
    def _loan_officer_candidates(self):
        """Real officers — the admin/root escape hatch (standing members of the
        group, ADR-0013) excluded, so their blanket membership never makes a
        genuinely single-officer setup look ambiguous."""
        officers = self.env.ref(
            "advance_payment.group_advance_payment_loan_officer"
        ).users - (self.env.ref("base.user_root") + self.env.ref("base.user_admin"))
        # A m2m read does not apply active_test, so archived officers would
        # otherwise still count towards "exactly one".
        return officers.filtered("active")

    @api.model
    def _default_loan_verifier_id(self):
        """The officer configured in Settings, else the sole real officer.

        The field is required (ADR-0013), so a multi-officer institute had no
        working default at all and every create — including the programmatic
        ones in the bridges — had to name an officer explicitly. Settings now
        carries the standing assignee; the sole-officer fallback keeps small
        setups working with no configuration (ADR-0015).
        """
        candidates = self._loan_officer_candidates()
        configured = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("advance_payment.default_loan_verifier_id")
        )
        if configured:
            # Ignore a stale setting: the user may have been deleted, archived
            # or dropped from the group since it was saved, and the field's own
            # domain would then reject the default.
            try:
                officer = self.env["res.users"].browse(int(configured))
            except (TypeError, ValueError):
                officer = self.env["res.users"]
            if officer & candidates:
                return officer.id
        return candidates.id if len(candidates) == 1 else False

    loan_verifier_id = fields.Many2one(
        comodel_name="res.users",
        string="เจ้าหน้าที่งานเงินยืม",
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref(
                    "advance_payment.group_advance_payment_loan_officer"
                ).ids,
            )
        ],
        default=_default_loan_verifier_id,
        required=True,
        tracking=True,
    )

    @api.model
    def _approver_candidates(self):
        """Members of the approver group who may be named as approver —
        matched the same way the field's own domain matches (direct
        membership), so a configured user can never resolve to a default the
        domain then rejects (ADR-0017)."""
        return self.env.ref(
            "advance_payment.group_advance_payment_loan_approver"
        ).users.filtered("active")

    @api.model
    def _default_approver_id(self):
        """The approver configured in Settings, else the admin.

        Approval is narrowed to the named approver (ADR-0017) and unlike the
        loan officer there is no "sole member" to infer — root/admin are
        standing members of the approver group. So the setting is the only
        real source, and the fallback is `base.user_admin`: required=True
        must always resolve, and an admin can approve anyway, so a database
        that never configured this still works instead of blocking every
        create (ADR-0016).
        """
        configured = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("advance_payment.default_approver_id")
        )
        if configured:
            # Ignore a stale setting the field's own domain would reject.
            try:
                approver = self.env["res.users"].browse(int(configured))
            except (TypeError, ValueError):
                approver = self.env["res.users"]
            if approver & self._approver_candidates():
                return approver.id
        return self.env.ref("base.user_admin").id

    approver_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติ",
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref(
                    "advance_payment.group_advance_payment_loan_approver"
                ).ids,
            )
        ],
        default=_default_approver_id,
        required=True,
        tracking=True,
        help="ผู้ที่จะได้รับงานให้อนุมัติเมื่อเจ้าหน้าที่ตรวจสอบคำขอเรียบร้อยแล้ว",
    )

    effective_date = fields.Date(
        string="Effective Date",
        readonly=True,
        copy=False,
        tracking=True,
        help="Date the disbursement transfer completed; the agreement becomes "
        "a formal debt (ลูกหนี้โดยสมบูรณ์) at this moment.",
    )

    # Actual-expense summary (บันทึกค่าใช้จ่ายจริง) — recorded on the agreement,
    # not itemized (ADR-0003).
    expense_description = fields.Text(
        string="คำอธิบายค่าใช้จ่าย",
        copy=False,
    )

    actual_expense_amount = fields.Monetary(
        string="ยอดค่าใช้จ่ายจริง",
        copy=False,
        tracking=True,
    )

    return_installment = fields.Boolean(
        string="คืนหลายงวด",
        copy=False,
        help="Allow the money to be returned in several transfers instead of "
        "one; the officer may toggle this in emergencies.",
    )

    amount_remaining = fields.Monetary(
        string="Amount Remaining",
        compute="_compute_amounts",
        store=True,
    )

    return_amount = fields.Monetary(
        string="ยอดที่ต้องคืน",
        compute="_compute_amounts",
        store=True,
        help="Loan amount minus the actual expense — the cash to return.",
    )

    excess_amount = fields.Monetary(
        string="เงินคืนส่วนเกิน",
        compute="_compute_amounts",
        store=True,
        help="Amount returned beyond the return amount; requires donation consent.",
    )

    # Informational usage records populated by integrations (e.g. the
    # disbursement bridge). The debt is driven by actual_expense_amount, not by
    # these lines — kept so bridges can extend the model.
    usage_line_ids = fields.One2many(
        comodel_name="advance.payment.usage.line",
        inverse_name="agreement_id",
        string="Usage Records",
        readonly=True,
        copy=False,
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
    date_verified = fields.Datetime(string="Date Verified", readonly=True, copy=False)
    date_approved = fields.Datetime(string="Date Approved", readonly=True, copy=False)
    date_closed = fields.Datetime(string="Date Closed", readonly=True, copy=False)

    terms_conditions = fields.Html(
        string="เงื่อนไขและข้อตกลงการยืมเงินทดรองจ่าย",
        default=lambda self: self.env["ir.config_parameter"]
        .sudo()
        .get_param("advance_payment.terms_conditions"),
        copy=True,
    )

    cancel_reason = fields.Text(string="Reason", readonly=True, copy=False)

    # Over-return donation consent (ADR-0003). The excess is never refunded —
    # the borrower must consent to donate it to the institute before closing.
    donate_excess = fields.Boolean(
        string="ยินยอมบริจาคเงินส่วนเกินให้สถาบัน",
        copy=False,
    )
    donate_consent_uid = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ยืนยันการบริจาค",
        readonly=True,
        copy=False,
    )
    donate_consent_date = fields.Datetime(
        string="เวลายืนยันการบริจาค",
        readonly=True,
        copy=False,
    )

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

    def _default_bank_id(self):
        """The borrower's first bank account, in res.partner.bank order.

        Picked outright rather than only when unambiguous: a borrower with
        several accounts should still not have to open the dropdown, and the
        officer may correct bank_id up to the transfer anyway (ADR-0005).
        Returns an empty recordset when the work contact has no account — the
        blocking exception rule on bank_id then catches it at submit.
        """
        self.ensure_one()
        partner = self.employee_id.work_contact_id
        if not partner:
            return self.env["res.partner.bank"]
        return self.env["res.partner.bank"].search(
            [("partner_id", "=", partner.id)], limit=1
        )

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        """Re-point bank_id at the new borrower, without making them pick.

        Also fires on form open (the client's initial onchange pass runs every
        onchange method), so a borrower drafting for themselves gets their
        account filled in from the start (ADR-0015).
        """
        if self.bank_id and self.bank_id.partner_id == self.employee_id.work_contact_id:
            return
        self.bank_id = self._default_bank_id()

    @api.depends(
        "loan_amount",
        "actual_expense_amount",
        "return_line_ids.amount",
        "return_line_ids.state",
    )
    def _compute_amounts(self):
        for rec in self:
            expense = rec.actual_expense_amount
            returned = sum(
                rec.return_line_ids.filtered(
                    lambda l: l.state == "done"
                ).mapped("amount")
            )
            rec.amount_returned = returned
            rec.amount_remaining = rec.loan_amount - expense - returned
            rec.return_amount = rec.loan_amount - expense
            rec.excess_amount = max(0.0, returned - rec.return_amount)

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

    @api.constrains("actual_expense_amount", "loan_amount")
    def _check_actual_expense(self):
        for rec in self:
            if rec.actual_expense_amount < 0:
                raise ValidationError(_("Actual expense cannot be negative."))
            if rec.actual_expense_amount > rec.loan_amount:
                raise ValidationError(
                    _("Actual expense cannot exceed the loan amount.")
                )

    @api.constrains("name")
    def _check_name_unique(self):
        for rec in self:
            if rec.name == _("New"):
                continue
            if self.search([("name", "=", rec.name), ("id", "!=", rec.id)], limit=1):
                raise ValidationError(
                    _("Agreement number '%(name)s' must be unique!", name=rec.name)
                )

    @api.constrains("employee_id", "user_id")
    def _check_creator_only(self):
        """No drafting on behalf: outside the `user` data-entry tier (and
        outside strict mode, ADR-0014), the borrower (employee_id) must be
        the drafter (user_id). A base.group_system admin, or a `user`-tier
        staffer drafting on behalf of a borrower, is exempt — the borrower
        still has to submit the request personally
        (_check_submit_permission)."""
        if self._can_draft_on_behalf():
            return
        for rec in self:
            if rec.employee_id.user_id != rec.user_id:
                raise ValidationError(
                    _(
                        "A loan must be created by the borrower — you cannot"
                        " borrow on behalf of someone else."
                    )
                )

    def _prepare_account_payment_vals(self, payment_type):
        vals = {
            "partner_id": self.partner_id.id,
            "amount": self.loan_amount,
            "currency_id": self.currency_id.id,
            "advance_payment_id": self.id,
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
        records = self.filtered(lambda s: s.state == "to_verify")
        if records:
            records._check_exception()

    def name_get(self):
        """Show the source document alongside the number, so a loan is
        identifiable from an m2o without opening it."""
        result = []
        for rec in self:
            # Always keyed on the ADV running number — it identifies the row for
            # its whole life; the contract number is searchable separately.
            name = rec.name
            if rec.reference:
                name = "%s (%s)" % (name, rec.reference.display_name)
            result.append((rec.id, name))
        return result

    def write(self, vals):
        protected = self._PROTECTED_FIELDS & set(vals)
        if protected:
            is_admin = self.env.user.has_group("base.group_system")
            is_loan_officer = self.env.user.has_group(
                "advance_payment.group_advance_payment_loan_officer"
            )
            for rec in self:
                if rec.state == "draft" or is_admin:
                    continue
                # Loan officer may still correct fields (ADR-0005):
                #  - all material fields while in to_verify
                #  - bank_id up to the transfer
                editable = set()
                if is_loan_officer and rec.state == "to_verify":
                    editable |= self._PROTECTED_FIELDS
                if is_loan_officer and rec.state in (
                    "to_verify",
                    "to_approve",
                    "waiting_transfer",
                ):
                    editable.add("bank_id")
                blocked = protected - editable
                if blocked:
                    raise UserError(
                        _(
                            "Cannot modify key field(s) of a submitted"
                            " agreement: %(fields)s",
                            fields=", ".join(sorted(blocked)),
                        )
                    )
        return super().write(vals)

    def unlink(self):
        """An agreement may only be deleted once cancelled (ยกเลิกก่อน) — a
        live/settled record is the audit trail, not scratch data. Any group
        with delete rights on the model is subject to this, base.group_system
        excepted (same escape hatch as write())."""
        if not self.env.user.has_group("base.group_system"):
            not_cancelled = self.filtered(lambda rec: rec.state != "cancel")
            if not_cancelled:
                raise UserError(
                    _(
                        "Cancel an agreement before deleting it: %(names)s",
                        names=", ".join(not_cancelled.mapped("name")),
                    )
                )
        return super().unlink()

    def button_draft(self):
        self.write({"state": "draft"})

    def button_cancel(self):
        self.write({"state": "cancel"})

    # ------------------------------------------------------------------ #
    # Front half: submit → verify → approve → transfer → in_progress       #
    # ------------------------------------------------------------------ #

    def _check_submit_permission(self):
        """Creator-only: only the borrower (or an admin) may submit (ADR-0005)."""
        is_admin = self.env.user.has_group("base.group_system")
        for rec in self:
            if rec.employee_id.user_id == self.env.user or is_admin:
                continue
            raise UserError(
                _("Only the borrower can submit this agreement (no borrowing on"
                  " behalf).")
            )

    def _check_one_active_agreement(self):
        """A borrower may hold only one active agreement at a time (ADR-0001)."""
        for rec in self:
            other = rec.sudo().search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("state", "in", self.ACTIVE_STATES),
                    ("id", "!=", rec.id),
                ],
                limit=1,
            )
            if other:
                raise UserError(
                    _(
                        "%(user)s already has an active loan agreement"
                        " (%(name)s). Clear it before starting a new one.",
                        user=rec.employee_id.name,
                        name=other.name,
                    )
                )

    def _workflow_activity_specs(self):
        """(summary, assignee) of the To-Do owned by each pending state.

        One entry per state that waits on a named person, keyed by that state
        so the transitions can name the stage they are leaving or entering
        rather than repeating a set of near-identical helpers (ADR-0015).
        """
        self.ensure_one()
        return {
            "to_verify": (
                _("ตรวจสอบคำขอยืมเงิน %s", self.name),
                self.loan_verifier_id,
            ),
            "to_approve": (
                _("อนุมัติคำขอยืมเงิน %s", self.name),
                self.approver_id,
            ),
        }

    def _workflow_activities(self, stage=None):
        """The records' open workflow To-Dos — one stage, or all of them.

        Matched on type *and* summary, not type alone: WORKFLOW_ACTIVITY_XMLID
        is the generic "To Do" type, so a blanket `activity_feedback` /
        `activity_unlink` would sweep up unrelated to-dos on the same record.
        """
        activity_type = self.env.ref(WORKFLOW_ACTIVITY_XMLID)
        wanted = set()
        for rec in self:
            specs = rec._workflow_activity_specs()
            for key in [stage] if stage else specs:
                wanted.add((rec.id, specs[key][0]))
        return self.activity_ids.filtered(
            lambda a: a.activity_type_id == activity_type
            and (a.res_id, a.summary) in wanted
        )

    def _schedule_workflow_activity(self, stage):
        """Raise `stage`'s To-Do on its assignee.

        Clears any stale one first so recall/resubmit loops (action_recall,
        the officer's own ส่งกลับแก้ไข) don't pile up duplicates on the same
        record (ADR-0013).
        """
        for rec in self:
            summary, assignee = rec._workflow_activity_specs()[stage]
            rec._drop_workflow_activities(stage)
            rec.activity_schedule(
                WORKFLOW_ACTIVITY_XMLID,
                user_id=assignee.id,
                summary=summary,
            )

    def _done_workflow_activity(self, stage, feedback):
        """Close `stage`'s To-Do — the step actually happened (ADR-0015).

        sudo: `mail_activity_rule_user` limits write/unlink to the activity's
        `user_id` or `create_uid`, which here are the stage's assignee and
        whoever moved the record into that stage. An admin acting on the
        assignee's behalf is neither, so the rule would block them. Authority
        is already established by the caller's own check, and sudo() keeps
        `env.uid`, so the done-message is still authored by the real actor.
        """
        self._workflow_activities(stage).sudo().action_feedback(feedback=feedback)

    def _drop_workflow_activities(self, stage=None):
        """Drop To-Dos without marking them done — the request left the stage
        without the step being taken (cancel / ส่งกลับแก้ไข / ดึงกลับ), so the
        assignee must not keep a to-do they can no longer act on, and it must
        not show up in their done history either (ADR-0015).

        sudo for the same reason as _done_workflow_activity — a manager
        cancelling is neither the to-do's assignee nor its creator.
        """
        self._workflow_activities(stage).sudo().unlink()

    def action_submit(self):
        """Submit the request for verification (draft → to_verify)."""
        self._check_submit_permission()
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft agreements can be submitted."))
            rec._check_one_active_agreement()
            if rec.detect_exceptions() and not rec.ignore_exception:
                return rec._popup_exceptions()
            if rec.name == _("New"):
                rec.name = self.env["ir.sequence"].next_by_code("advance.payment")
            rec.date_submitted = fields.Datetime.now()
            rec.state = "to_verify"
            rec.message_post(
                body=_(
                    "Agreement submitted for verification by <b>%(user)s</b>."
                    " Loan amount: <b>%(amount)s %(currency)s</b>.",
                    user=rec.employee_id.name,
                    amount=rec.loan_amount,
                    currency=rec.currency_id.name,
                ),
                subtype_xmlid="mail.mt_note",
            )
            rec._schedule_workflow_activity("to_verify")

    def _check_verify_permission(self):
        """Officer-only: only the assigned loan officer (or an admin) may
        verify — not any loan-officer-group member (ADR-0013)."""
        is_admin = self.env.user.has_group("base.group_system")
        for rec in self:
            if is_admin or rec.loan_verifier_id == self.env.user:
                continue
            raise UserError(
                _(
                    "Only the assigned loan officer (%(officer)s) can verify"
                    " this agreement.",
                    officer=rec.loan_verifier_id.name,
                )
            )

    def action_verify(self):
        """Finance officer confirms the document check (to_verify → to_approve)."""
        self._check_verify_permission()
        for rec in self:
            if rec.state != "to_verify":
                raise UserError(_("Only agreements under verification can be verified."))
            rec.write({"state": "to_approve", "date_verified": fields.Datetime.now()})
            rec._done_workflow_activity(
                "to_verify",
                _("ตรวจสอบคำขอเรียบร้อย โดย %s", self.env.user.name),
            )
            rec._schedule_workflow_activity("to_approve")
            rec.message_post(
                body=_("ตรวจสอบคำขอเรียบร้อย ส่งเข้าขั้นอนุมัติ โดย <b>%(user)s</b>.",
                       user=self.env.user.name),
                subtype_xmlid="mail.mt_note",
            )

    def _check_approve_permission(self):
        """Approver-only: only the named approver (or an admin) may approve —
        not any loan-approver-group member (ADR-0017)."""
        is_admin = self.env.user.has_group("base.group_system")
        for rec in self:
            if is_admin or rec.approver_id == self.env.user:
                continue
            raise UserError(
                _(
                    "Only the assigned approver (%(approver)s) can approve"
                    " this agreement.",
                    approver=rec.approver_id.name,
                )
            )

    def action_approve(self):
        """Approve and create the outbound disbursement payment
        (to_approve → waiting_transfer).

        The voucher is deliberately left a **finance-office draft**
        (`finance_state = 'draft'`). Approval hands the money over; it does not
        advance it. The finance office's own first press — ยืนยันพร้อมส่งธนาคาร,
        `account.payment.action_confirm_for_bank()` — is what freezes the money
        side, numbers the ใบสำคัญจ่าย and makes the voucher eligible for an
        e-payment file, and it needs a paying account (หัวจ่าย) that this module
        has no business choosing. `account_payment.action_post` then closes the
        loop back to `action_start()` once the transfer is booked.
        """
        self._check_approve_permission()
        for rec in self:
            if rec.state != "to_approve":
                raise UserError(_("Only agreements awaiting approval can be approved."))
        payment_type = self.env.ref(
            "advance_payment.payment_type_advance_payment_outbound"
        )
        vals_list = [rec._prepare_account_payment_vals(payment_type) for rec in self]
        payments = self.env["account.payment"].create(vals_list)
        self.write(
            {
                "state": "waiting_transfer",
                "disbursement_state": "pending",
                "date_approved": fields.Datetime.now(),
            }
        )
        self._done_workflow_activity(
            "to_approve", _("อนุมัติคำขอเรียบร้อย โดย %s", self.env.user.name)
        )
        for rec, payment in zip(self, payments):
            rec.message_post(
                body=_(
                    "Agreement approved. Payment"
                    " <a href='/web#id=%(id)s&amp;model=account.payment'><b>%(name)s</b></a>"
                    " created for <b>%(amount)s %(currency)s</b> to <b>%(partner)s</b>."
                    " ขั้นตอนถัดไป: รอฝ่ายการเงินดำเนินการโอนเงิน",
                    id=payment.id,
                    name=payment.name,
                    amount=payment.amount,
                    currency=payment.currency_id.name,
                    partner=payment.partner_id.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    def action_start(self, payment=None):
        """Transfer completed → the loan becomes a formal debt.
        (waiting_transfer → in_progress). Triggered by payment posting."""
        for rec in self:
            vals = {"state": "in_progress"}
            if not rec.effective_date:
                vals["effective_date"] = (
                    payment.date if payment else fields.Date.context_today(rec)
                )
            if not rec.contract_number:
                vals["contract_number"] = self.env["ir.sequence"].next_by_code(
                    "advance.payment.contract"
                )
            rec.write(vals)
            body = _(
                "โอนเงินยืมสำเร็จ — เป็นลูกหนี้โดยสมบูรณ์ เลขที่สัญญา"
                " <b>%(contract)s</b> วันที่มีผล <b>%(date)s</b>."
                " ขั้นตอนถัดไป: ใช้เงินตามวัตถุประสงค์ แล้วนำส่งรายงานค่าใช้จ่าย",
                contract=rec.contract_number or "-",
                date=rec.effective_date or "-",
            )
            rec.message_post(body=body, subtype_xmlid="mail.mt_note")

    # ------------------------------------------------------------------ #
    # Recall / reset (before approval)                                     #
    # ------------------------------------------------------------------ #

    def action_recall(self):
        """Borrower pulls a not-yet-approved request back to draft (ADR-0001)."""
        self.ensure_one()
        if self.employee_id.user_id != self.env.user and not self.env.user.has_group(
            "base.group_system"
        ):
            raise UserError(_("Only the borrower can recall this request."))
        if self.state not in ("to_verify", "to_approve"):
            raise UserError(_("Only a not-yet-approved request can be recalled."))
        self.state = "draft"
        self._drop_workflow_activities()
        self.message_post(
            body=_("ดึงคำขอกลับเพื่อแก้ไข โดย <b>%(user)s</b>.", user=self.env.user.name),
            subtype_xmlid="mail.mt_note",
        )

    def action_reset_to_draft(self):
        """Finance officer resets a request under verification to draft (ADR-0001)."""
        for rec in self:
            if rec.state != "to_verify":
                raise UserError(
                    _("Only agreements under verification can be reset to draft.")
                )
            rec.state = "draft"
            rec._drop_workflow_activities()
            rec.message_post(
                body=_("ส่งกลับแก้ไข โดยเจ้าหน้าที่ <b>%(user)s</b>.",
                       user=self.env.user.name),
                subtype_xmlid="mail.mt_note",
            )

    def action_reset_cancel_to_draft(self):
        """Manager reopens a cancelled agreement back to draft (ad-hoc recovery).

        Only before the money moved: once the transfer completed
        (`effective_date`) the record carries a contract number, an expense
        report and return lines from its first cycle, and re-approving would
        mint a second disbursement payment (ADR-0012).
        """
        for rec in self:
            if rec.state != "cancel":
                raise UserError(
                    _("Only a cancelled agreement can be reset to draft.")
                )
            if rec.effective_date:
                raise UserError(
                    _("เงินยืมนี้โอนออกไปแล้ว ไม่สามารถตั้งกลับเป็นแบบร่างได้"
                      " — ให้ทำสัญญาฉบับใหม่")
                )
            rec.write(
                {
                    "state": "draft",
                    "cancel_reason": False,
                    "date_submitted": False,
                    "date_verified": False,
                    "date_approved": False,
                }
            )
            rec.message_post(
                body=_("ตั้งสัญญาที่ยกเลิกกลับเป็นแบบร่าง โดย <b>%(user)s</b>.",
                       user=self.env.user.name),
                subtype_xmlid="mail.mt_note",
            )

    # ------------------------------------------------------------------ #
    # Settle: report → reconcile → close                                   #
    # ------------------------------------------------------------------ #

    def action_submit_report(self):
        """Borrower submits the actual-expense report (in_progress → to_verify_report)."""
        for rec in self:
            if rec.state != "in_progress":
                raise UserError(
                    _("Only in-progress agreements can submit an expense report.")
                )
            if not rec.expense_description:
                raise UserError(
                    _("Record the actual expense (description + amount) before"
                      " submitting the report.")
                )
            rec.state = "to_verify_report"
            rec.message_post(
                body=_(
                    "นำส่งรายงานค่าใช้จ่าย: ใช้จริง <b>%(used)s</b>,"
                    " ต้องคืน <b>%(left)s</b> %(currency)s",
                    used=rec.actual_expense_amount,
                    left=rec.return_amount,
                    currency=rec.currency_id.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    def action_accept_report(self):
        """Finance officer accepts the expense report (to_verify_report → ...).
        No amount to return → close; return_amount > 0 → to_reconcile."""
        for rec in self:
            if rec.state != "to_verify_report":
                raise UserError(_("Only submitted reports can be accepted."))
            if rec.return_amount <= 0:
                rec.message_post(
                    body=_("ตรวจรับรายงานค่าใช้จ่าย ไม่มีเงินต้องคืน ปิดสัญญา"),
                    subtype_xmlid="mail.mt_note",
                )
                rec._do_close()
            else:
                rec.state = "to_reconcile"
                rec.message_post(
                    body=_(
                        "ตรวจรับรายงานค่าใช้จ่าย ต้องคืน <b>%(left)s %(currency)s</b>"
                        " รอผู้ยืมโอนคืน",
                        left=rec.return_amount,
                        currency=rec.currency_id.name,
                    ),
                    subtype_xmlid="mail.mt_note",
                )

    def action_confirm_donation(self):
        """Borrower consents to donate the over-returned excess (ADR-0003)."""
        self.ensure_one()
        if self.excess_amount <= 0:
            raise UserError(_("There is no excess to donate."))
        self.write(
            {
                "donate_excess": True,
                "donate_consent_uid": self.env.user.id,
                "donate_consent_date": fields.Datetime.now(),
            }
        )
        self.message_post(
            body=_(
                "ยินยอมบริจาคเงินส่วนเกิน <b>%(amount)s %(currency)s</b>"
                " ให้สถาบัน โดย <b>%(user)s</b>",
                amount=self.excess_amount,
                currency=self.currency_id.name,
                user=self.env.user.name,
            ),
            subtype_xmlid="mail.mt_note",
        )
        self._try_auto_close()

    def _try_auto_close(self):
        """Auto-close when the debt is settled (ADR-0003)."""
        for rec in self:
            if rec.state != "to_reconcile":
                continue
            if rec.amount_remaining > 0:
                continue  # still owes money
            if rec.excess_amount > 0 and not rec.donate_excess:
                continue  # over-return needs donation consent first
            rec._do_close()

    def action_close(self):
        """Officer closes from to_verify_report when there is no leftover."""
        self.ensure_one()
        if self.state == "to_verify_report" and self.return_amount <= 0:
            return self._do_close()
        raise UserError(
            _("An agreement closes automatically once the debt is fully settled.")
        )

    def _do_close(self):
        """Close the agreement (ปิดสัญญา)."""
        for rec in self:
            if rec.state not in ("to_verify_report", "to_reconcile"):
                raise UserError(_("This agreement cannot be closed from its state."))
            rec.date_closed = fields.Datetime.now()
            rec.state = "done"
            rec.message_post(
                body=_(
                    "ปิดสัญญา ใช้จริง <b>%(used)s</b> คืน <b>%(returned)s</b>"
                    " %(currency)s",
                    used=rec.actual_expense_amount,
                    returned=rec.amount_returned,
                    currency=rec.currency_id.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    def action_reopen(self):
        """Reopen a closed agreement (ERP admin only)."""
        for rec in self:
            if rec.state != "done":
                raise UserError(_("Only closed agreements can be reopened."))
            rec.date_closed = False
            rec.state = "to_reconcile" if rec.return_amount > 0 else "in_progress"
            rec.message_post(
                body=_("Agreement reopened by <b>%(user)s</b>.", user=self.env.user.name),
                subtype_xmlid="mail.mt_note",
            )

    # ------------------------------------------------------------------ #
    # Cancel / reject                                                      #
    # ------------------------------------------------------------------ #

    def action_open_cancel_wizard(self):
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
        """Void this loan's vouchers so a cancelled agreement leaves none live.

        `account.payment.state` is Odoo's own draft/posted/cancel — the finance
        office's status is the separate `finance_state` (finance_kmitl), so
        there is no "submitted" payment state to unwind here. A voucher the
        finance office has already confirmed for the bank keeps
        `finance_state = 'confirmed'` after this: unwinding that is their call,
        not the loan's, and the numbered ใบสำคัญจ่าย has to stay auditable.
        """
        for payment in self.payment_ids.filtered(lambda p: p.state != "cancel"):
            if payment.state == "posted":
                payment.action_draft()
            payment.action_cancel()

    def _action_do_cancel(self, reason):
        self.ensure_one()
        if self.state not in (
            "to_verify",
            "to_approve",
            "waiting_transfer",
            "in_progress",
            "to_verify_report",
            "to_reconcile",
        ):
            raise UserError(_("This agreement cannot be cancelled from its state."))
        self._cancel_payments()
        self.write(
            {"state": "cancel", "cancel_reason": reason, "disbursement_state": False}
        )
        self._drop_workflow_activities()
        self.message_post(
            body=_("Agreement cancelled. Reason: %(reason)s", reason=reason),
            subtype_xmlid="mail.mt_note",
        )

    def _action_do_reject(self, reason=False):
        """Finance officer sends the request back to draft (to_verify → draft)."""
        self.ensure_one()
        if self.state != "to_verify":
            raise UserError(_("Only agreements under verification can be sent back."))
        vals = {"state": "draft"}
        if reason:
            vals["cancel_reason"] = reason
        self.write(vals)
        self._drop_workflow_activities()
        body = (
            _("Agreement returned to draft. Reason: %(reason)s", reason=reason)
            if reason
            else _("ส่งกลับแก้ไข")
        )
        self.message_post(body=body, subtype_xmlid="mail.mt_note")

    def action_reject(self):
        self.ensure_one()
        self._action_do_reject()

    # ------------------------------------------------------------------ #
    # Smart buttons / wizards                                              #
    # ------------------------------------------------------------------ #

    def action_view_payments(self):
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

    def action_open_return_wizard(self):
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
