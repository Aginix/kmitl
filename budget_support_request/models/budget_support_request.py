from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext

OFFICER_GROUP_XMLID = "budget_support_request.group_budget_support_officer"
FULFIL_ACTIVITY = "budget_support_request.mail_activity_support_fulfil"
ACK_ACTIVITY = "budget_support_request.mail_activity_support_ack"


class BudgetSupportRequest(models.Model):
    """ขอรับการสนับสนุนงบประมาณ — a requesting unit's application for central to
    allocate budget onto its ``departments`` dimension.

    The request only carries the *ask* (department, amount, reason, files);
    central chooses the funding source and fulfils it, after approval, with
    either a ``budget.transfer`` (โอน) or a ``budget.commitment`` (จอง) — see
    ``CONTEXT.md``. ``_mail_post_access = "read"`` lets the notify-only
    ``group_budget_support_officer`` (read, no write) still see and complete
    the Todo scheduled on approval.
    """

    _name = "budget.support.request"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _description = "Budget Support Request"
    _order = "date desc, name desc, id desc"
    _mail_post_access = "read"

    name = fields.Char(
        string="Request Number",
        compute="_compute_name",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
        tracking=True,
    )
    _analytic_keys = {"departments": "department_analytic_id"}

    def _inverse_department_analytic(self):
        for record in self:
            record._update_analytic_distribution("departments")

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        tracking=True,
        readonly=False,
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        tracking=True,
    )
    amount_requested = fields.Monetary(
        string="จำนวนเงินที่ขอ",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    reason = fields.Html(
        string="เหตุผล/ความจำเป็น",
        sanitize=True,
        tracking=True,
        help="Please explain why this budget support is needed.",
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="budget_support_request_attachment_rel",
        column1="request_id",
        column2="attachment_id",
        string="เอกสารแนบ",
    )

    user_id = fields.Many2one(
        string="ผู้ขอ",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        required=True,
    )
    approver_id = fields.Many2one(
        string="Approved by",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        readonly=True,
    )
    approval_date = fields.Datetime(
        string="Approval Date",
        copy=False,
        tracking=True,
        readonly=True,
    )

    transfer_ids = fields.One2many(
        comodel_name="budget.transfer",
        inverse_name="support_request_id",
        string="Budget Transfers",
    )
    commitment_ids = fields.One2many(
        comodel_name="budget.commitment",
        inverse_name="support_request_id",
        string="Budget Commitments",
    )
    transfer_count = fields.Integer(compute="_compute_fulfilment_counts")
    commitment_count = fields.Integer(compute="_compute_fulfilment_counts")

    show_submit_button = fields.Boolean(compute="_compute_button_visibility")
    show_approve_button = fields.Boolean(compute="_compute_button_visibility")
    show_fulfil_transfer_button = fields.Boolean(compute="_compute_button_visibility")
    show_fulfil_reserve_button = fields.Boolean(compute="_compute_button_visibility")
    show_done_button = fields.Boolean(compute="_compute_button_visibility")
    show_cancel_button = fields.Boolean(compute="_compute_button_visibility")
    show_reset_button = fields.Boolean(compute="_compute_button_visibility")

    # Single flag driving every "editable while …" attrs in the form. The
    # base opens editing in ``draft`` only; a module that adds intermediate
    # states — e.g. ``budget_support_request_sarabun`` reopening a
    # ``returned`` letter — extends ``_compute_can_edit`` instead of
    # overriding each field's attrs (mirrors ``budget.transfer.can_edit``).
    can_edit = fields.Boolean(compute="_compute_can_edit")

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("state", "account_fiscal_year_id")
    def _compute_name(self):
        """Mint the request number once it leaves draft (mirrors
        ``budget.transfer._compute_name``): the year comes from the fiscal
        year's end date, not the day the number happens to be minted."""
        placeholders = {"New", _("New")}
        for request in self:
            if request.state == "cancelled":
                continue
            has_name = request.name and request.name not in placeholders
            if has_name or request.state == "draft":
                continue
            if not has_name and request.account_fiscal_year_id:
                request.name = (
                    self.env["ir.sequence"]
                    .with_context(
                        ir_sequence_date=request.account_fiscal_year_id.date_to
                    )
                    .next_by_code("budget.support.request")
                ) or _("New")

    @api.depends("state")
    def _compute_can_edit(self):
        for request in self:
            request.can_edit = request.state == "draft"

    @api.depends("transfer_ids", "commitment_ids")
    def _compute_fulfilment_counts(self):
        for request in self:
            request.transfer_count = len(request.transfer_ids)
            request.commitment_count = len(request.commitment_ids)

    @api.depends("state", "user_id")
    def _compute_button_visibility(self):
        user = self.env.user
        is_manager = user.has_group("budget.group_budget_manager")
        is_admin = self.env.is_admin()
        for request in self:
            request.show_submit_button = request.state == "draft" and (
                request.user_id == user or is_admin
            )
            request.show_approve_button = request.state == "submitted"
            can_fulfil = request.state in ("approved", "in_progress") and (
                is_manager or is_admin
            )
            request.show_fulfil_transfer_button = can_fulfil
            request.show_fulfil_reserve_button = can_fulfil
            request.show_done_button = request.state == "in_progress" and (
                is_manager or is_admin
            )
            request.show_cancel_button = request.state in ("draft", "submitted")
            request.show_reset_button = (
                request.state == "submitted" and (request.user_id == user or is_admin)
            ) or (request.state == "cancelled" and (is_manager or is_admin))

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange("date")
    def _onchange_date(self):
        if self.date:
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", self.date),
                    ("date_to", ">=", self.date),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if fiscal_year:
                self.account_fiscal_year_id = fiscal_year

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        if not (
            self.env.user.has_group("budget.group_budget_user")
            or self.env.is_admin()
        ):
            raise UserError(_("Only Budget Users can submit a support request."))
        self._validate_request_data()
        self.write({"state": "submitted"})
        return True

    def action_approve(self):
        is_admin = self.env.is_admin()
        if not (
            self.env.user.has_group("budget.group_budget_manager") or is_admin
        ):
            raise UserError(_("Only Budget Managers can approve support requests."))
        if not is_admin:
            for request in self:
                if request.user_id == self.env.user:
                    raise UserError(
                        _("You cannot approve your own budget support request.")
                    )
        self._validate_request_data()
        self.write(
            {
                "state": "approved",
                "approver_id": self.env.user.id,
                "approval_date": fields.Datetime.now(),
            }
        )
        self._after_approved()
        return True

    def action_fulfil_transfer(self):
        self.ensure_one()
        self._check_can_fulfil()
        vals = self._prepare_transfer_vals()
        return {
            "type": "ir.actions.act_window",
            "name": _("Budget Transfer"),
            "res_model": "budget.transfer",
            "view_mode": "form",
            "target": "current",
            "context": {("default_%s" % key): value for key, value in vals.items()},
        }

    def action_fulfil_reserve(self):
        self.ensure_one()
        self._check_can_fulfil()
        vals = self._prepare_commitment_vals()
        return {
            "type": "ir.actions.act_window",
            "name": _("Budget Commitment"),
            "res_model": "budget.commitment",
            "view_mode": "form",
            "target": "current",
            "context": {("default_%s" % key): value for key, value in vals.items()},
        }

    def action_done(self):
        is_admin = self.env.is_admin()
        if not (
            self.env.user.has_group("budget.group_budget_manager") or is_admin
        ):
            raise UserError(_("Only Budget Managers can close a support request."))
        if self.filtered(lambda r: r.state != "in_progress"):
            raise UserError(_("Only a request in progress can be marked done."))
        self.write({"state": "done"})
        self._after_done()
        return True

    def action_cancel(self):
        """Block only once central has acted on the request — a bridge that
        adds its own pre-approval states (e.g. ``sent``/``returned``) stays
        cancellable through here without needing to loosen this check."""
        if self.filtered(lambda r: r.state in ("approved", "in_progress", "done")):
            raise UserError(
                _("An approved or fulfilled request cannot be cancelled.")
            )
        self.write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        """Only guards the states the base itself reaches (``submitted``,
        ``cancelled``); a bridge introducing extra pre-approval states
        (``sent``/``returned``/``rejected``) adds its own guards on top of
        this, rather than this method blocking them outright."""
        user = self.env.user
        is_manager = user.has_group("budget.group_budget_manager")
        is_admin = self.env.is_admin()
        for request in self:
            if request.state == "submitted" and not (
                request.user_id == user or is_admin
            ):
                raise UserError(
                    _("Only the requester can reset a submitted request to draft.")
                )
            if request.state == "cancelled" and not (is_manager or is_admin):
                raise UserError(
                    _("Only Budget Managers can reset a cancelled request to draft.")
                )
        self.write({"state": "draft", "approver_id": False, "approval_date": False})
        return True

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate_request_data(self):
        self.ensure_one()
        if not self.department_analytic_id:
            raise ValidationError(
                _("Please select the requesting unit's department dimension.")
            )
        if not self.account_fiscal_year_id:
            raise ValidationError(_("Please set the fiscal year."))
        if self.amount_requested <= 0:
            raise ValidationError(_("The requested amount must be greater than zero."))
        if not (self.reason and html2plaintext(self.reason).strip()):
            raise ValidationError(_("Please provide a reason/justification."))

    def action_view_transfers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Budget Transfers"),
            "res_model": "budget.transfer",
            "view_mode": "tree,form",
            "domain": [("support_request_id", "=", self.id)],
        }

    def action_view_commitments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Budget Commitments"),
            "res_model": "budget.commitment",
            "view_mode": "tree,form",
            "domain": [("support_request_id", "=", self.id)],
        }

    def _check_can_fulfil(self):
        self.ensure_one()
        if self.state not in ("approved", "in_progress"):
            raise UserError(_("Only an approved support request can be fulfilled."))
        if not (
            self.env.user.has_group("budget.group_budget_manager")
            or self.env.is_admin()
        ):
            raise UserError(_("Only Budget Managers can fulfil a support request."))

    # ------------------------------------------------------------------
    # Hooks (bridges extend)
    # ------------------------------------------------------------------
    def _after_approved(self):
        """Notify the read-only officer group that a request is ready to fulfil."""
        officer_group = self.env.ref(OFFICER_GROUP_XMLID, raise_if_not_found=False)
        if not officer_group:
            return
        for request in self:
            for user in officer_group.users:
                request.activity_schedule(FULFIL_ACTIVITY, user_id=user.id)

    def _after_done(self):
        """Clear the officer's fulfilment Todo and notify the requester."""
        self.activity_feedback([FULFIL_ACTIVITY])
        for request in self:
            request.activity_schedule(ACK_ACTIVITY, user_id=request.user_id.id)

    def _on_fulfilment_posted(self):
        """Move an approved request to in_progress once central has posted a
        transfer or reserved a commitment against it. Idempotent."""
        self.filtered(lambda r: r.state == "approved").write(
            {"state": "in_progress"}
        )

    def _prepare_transfer_vals(self):
        """Default values for the draft ``budget.transfer`` opened by
        :meth:`action_fulfil_transfer`. ``account_id`` on the TO line is left
        unset — it is a hard required field with no default, so it is filled
        in by central on the (unsaved) form rather than at creation time."""
        self.ensure_one()
        return {
            "move_type": "entry",
            "reason": html2plaintext(self.reason or ""),
            "date": self.date,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "department_analytic_id": self.department_analytic_id.id,
            "support_request_id": self.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "transfer_direction": "to",
                        "amount": self.amount_requested,
                        "department_analytic_id": self.department_analytic_id.id,
                    },
                )
            ],
        }

    def _prepare_commitment_vals(self):
        """Default values for the draft ``budget.commitment`` opened by
        :meth:`action_fulfil_reserve`. No ``line_ids`` — the native Reserve
        button synthesizes the reserve line from the header. ``account_id``
        is left for central to fill in on the form (see
        :meth:`_prepare_transfer_vals`)."""
        self.ensure_one()
        return {
            "title": _("สนับสนุน %s") % (self.name or ""),
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "amount": self.amount_requested,
            "support_request_id": self.id,
        }
