from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext

BUDDY_GROUP_XMLID = "budget_buddy.group_budget_buddy"
# Central only supports units out of เงินรายได้ (the `sources` code), so the
# request's แหล่งเงิน is fixed rather than asked for.
SOURCE_REVENUE_CODE = "2"
FULFIL_ACTIVITY = "budget_support_request.mail_activity_support_fulfil"
ACK_ACTIVITY = "budget_support_request.mail_activity_support_ack"


class BudgetSupportRequest(models.Model):
    """ขอรับการสนับสนุนงบประมาณ — a requesting unit's application for central to
    allocate budget onto its ``departments`` dimension.

    The request only carries the *ask* (department, amount, reason, files);
    central chooses the funding source and fulfils it, after approval, with
    either a ``budget.transfer`` (โอน) or a ``budget.commitment`` (จอง) — see
    ``CONTEXT.md``. ``_mail_post_access = "read"`` keeps the fulfilment Todo
    readable by anyone who can read the request, without requiring write.
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
        # Stored so the list/search view can search and group by the ส่วนงาน
        # dimension (mirrors kmitl.project / procurement.plan) — read_group
        # rejects non-stored fields and a non-stored leaf is silently dropped
        # from the search domain.
        store=True,
        tracking=True,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงินงบประมาณ",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=True,
        readonly=True,
        tracking=True,
        help="Fixed: central supports units out of งบประมาณเงินรายได้ only.",
    )
    _analytic_keys = {
        "departments": "department_analytic_id",
        "sources": "source_analytic_id",
    }

    def _inverse_department_analytic(self):
        for record in self:
            record._update_analytic_distribution("departments")

    def _inverse_source_analytic(self):
        for record in self:
            record._update_analytic_distribution("sources")

    @api.model
    def _default_source_analytic(self):
        return self.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "sources"), ("code", "=", SOURCE_REVENUE_CODE)],
            limit=1,
        )

    @api.constrains("source_analytic_id", "analytic_distribution")
    def _check_source_is_fixed(self):
        """``readonly`` only stops the form; the แหล่งเงิน is fixed for every
        support request, so hold it over RPC and over a hand-written
        ``analytic_distribution`` too."""
        fixed = self._default_source_analytic()
        if not fixed:
            return
        for request in self:
            if request.source_analytic_id and request.source_analytic_id != fixed:
                raise ValidationError(
                    _(
                        "แหล่งเงินของคำขอรับการสนับสนุนถูกกำหนดเป็น %(fixed)s "
                        "เท่านั้น (ได้รับ %(given)s)"
                    )
                    % {
                        "fixed": fixed.display_name,
                        "given": request.source_analytic_id.display_name,
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Stamp the fixed แหล่งเงิน server-side. It cannot ride on a plain
        ``default``: the field is readonly, and the web client drops readonly
        fields on save, so the value would never reach
        ``analytic_distribution``."""
        source = self._default_source_analytic()
        if source:
            for vals in vals_list:
                vals.setdefault("source_analytic_id", source.id)
        return super().create(vals_list)

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
    # One2many on ``res_id`` (never a Many2many — mirrors
    # budget_transfer_attachment): the ``many2many_binary`` widget uploads with
    # ``res_id = 0`` while the record is still unsaved, and a Many2many would
    # leave it at 0 forever, which makes ``ir.attachment.check()`` hide the file
    # from everyone but the uploader (the approver included). The One2many
    # inverse stamps ``res_id`` on save, so the link self-heals.
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="เอกสารแนบ",
        domain=[("res_model", "=", "budget.support.request")],
    )

    # Locked on purpose (CONTEXT.md ▸ Requester): the request stays attributed
    # to whoever filed it, which is what makes "an approver may not approve
    # their own request" meaningful — a reassignable requester would hand
    # anyone a way around that check.
    user_id = fields.Many2one(
        string="ผู้ขอ",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
    )
    officer_id = fields.Many2one(
        string="เจ้าหน้าที่ Buddy ผู้รับผิดชอบ",
        comodel_name="res.users",
        compute="_compute_officer_id",
        store=True,
        readonly=False,
        copy=False,
        tracking=True,
        domain=lambda self: [("groups_id", "in", self.env.ref(BUDDY_GROUP_XMLID).ids)],
        help="The one central-office Buddy who will fulfil this request and who "
        "receives the Todo when it is approved. Defaults (in draft) to the Buddy "
        "covering this unit in the Buddy settings; the requesting unit may name "
        "another.",
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

    # True once the BSR number has been minted — the fiscal year is then frozen
    # (it drives the number's year), even after a Reset to Draft or a ตีกลับ
    # reopening the request (mirrors ``budget.transfer.fiscal_year_locked``).
    fiscal_year_locked = fields.Boolean(compute="_compute_fiscal_year_locked")

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("name")
    def _compute_fiscal_year_locked(self):
        placeholders = {"New", _("New")}
        for request in self:
            request.fiscal_year_locked = bool(
                request.name and request.name not in placeholders
            )

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

    def _get_buddies(self):
        """Buddies whose coverage rows match this request, primary first.
        Evaluated on demand: a row's domain may read any field, so it cannot
        sit behind a cache keyed on the unit alone (mirrors
        ``budget_transfer_verify``)."""
        self.ensure_one()
        return self.env["budget.buddy"]._get_buddy_users(self)

    def _buddy_can_read(self, user):
        """Whether ``user``'s record rules let them read this request —
        evaluated in memory so it also works on an unsaved record."""
        self.ensure_one()
        domain = self.env["ir.rule"].with_user(user)._compute_domain(self._name)
        return not domain or bool(self.sudo().filtered_domain(domain))

    def _get_assignable_buddies(self):
        """Covering buddies who can actually read the request — a Buddy the OU
        rule hides it from could never open the Todo, so never offer them."""
        self.ensure_one()
        return self._get_buddies().filtered(self._buddy_can_read)

    @api.depends("department_analytic_id", "user_id", "amount_requested")
    def _compute_officer_id(self):
        """Default the Buddy from the coverage settings while in draft; a row's
        domain may read any field, so the depends cover the usual ones. A Buddy
        the settings still assign is kept, so editing the request does not undo
        the unit's own pick."""
        for request in self:
            if request.state == "draft":
                buddies = request._get_assignable_buddies()
                if request.officer_id not in buddies:
                    request.officer_id = buddies[:1]
            else:
                request.officer_id = request.officer_id

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
            request.show_approve_button = request.state == "submitted" and (
                is_manager or is_admin
            )
            can_fulfil = request.state in ("approved", "in_progress") and (
                is_manager or is_admin
            )
            request.show_fulfil_transfer_button = can_fulfil
            request.show_fulfil_reserve_button = can_fulfil
            request.show_done_button = request.state == "in_progress" and (
                is_manager or is_admin
            )
            request.show_cancel_button = request.state in ("draft", "submitted")
            # Reopening past `submitted` is the Budget Manager's alone
            # (CONTEXT.md ▸ Reopening).
            request.show_reset_button = (
                request.state == "submitted" and (request.user_id == user or is_admin)
            ) or (
                request.state in ("cancelled", "approved", "in_progress", "done")
                and (is_manager or is_admin)
            )

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
        user = self.env.user
        is_admin = self.env.is_admin()
        if not (user.has_group("budget.group_budget_user") or is_admin):
            raise UserError(_("Only Budget Users can submit a support request."))
        for request in self:
            if request.user_id != user and not is_admin:
                raise UserError(
                    _("Only the requester can submit their own support request.")
                )
            if not request.officer_id:
                raise UserError(
                    _(
                        "กรุณาระบุเจ้าหน้าที่ Buddy ผู้รับผิดชอบ (ส่วนงาน %s "
                        "ยังไม่มีเจ้าหน้าที่ Buddy ที่มีสิทธิ์เข้าถึงคำขอนี้ในการตั้งค่า)"
                    )
                    % (request.department_analytic_id.display_name or "-")
                )
            if not request._buddy_can_read(request.officer_id):
                raise UserError(
                    _("%s ไม่มีสิทธิ์เข้าถึงคำขอนี้ กรุณาเลือกเจ้าหน้าที่ Buddy คนอื่น")
                    % request.officer_id.name
                )
        self._validate_request_data()
        self.write({"state": "submitted"})
        return True

    def action_approve(self):
        is_admin = self.env.is_admin()
        if not (self.env.user.has_group("budget.group_budget_manager") or is_admin):
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
        if not (self.env.user.has_group("budget.group_budget_manager") or is_admin):
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
            raise UserError(_("An approved or fulfilled request cannot be cancelled."))
        self.write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        """The requester may take back their own `submitted` request; every
        other state is the Budget Manager's to reopen. A bridge introducing
        extra states (``sent``/``returned``/``rejected``) adds its own guards
        on top — ``sent`` is refused outright by the e-Saraban bridge."""
        user = self.env.user
        is_manager = user.has_group("budget.group_budget_manager")
        is_admin = self.env.is_admin()
        for request in self:
            if request.state == "submitted":
                if not (request.user_id == user or is_admin):
                    raise UserError(
                        _("Only the requester can reset a submitted request to draft.")
                    )
            elif request.state != "draft" and not (is_manager or is_admin):
                # Everything past `submitted` — including a decided or already
                # fulfilled request — is the Budget Manager's to reopen
                # (CONTEXT.md ▸ Reopening). The allocations already made keep
                # pointing at it; settling those is a separate act.
                raise UserError(_("Only Budget Managers can reopen this request."))
        self.write({"state": "draft", "approver_id": False, "approval_date": False})
        return True

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate_request_data(self):
        """Validate every record in ``self`` — ``action_submit`` /
        ``action_approve`` are multi-record capable."""
        for request in self:
            if not request.department_analytic_id:
                raise ValidationError(
                    _("Please select the requesting unit's department dimension.")
                )
            if not request.account_fiscal_year_id:
                raise ValidationError(_("Please set the fiscal year."))
            if request.amount_requested <= 0:
                raise ValidationError(
                    _("The requested amount must be greater than zero.")
                )
            if not (request.reason and html2plaintext(request.reason).strip()):
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
        """Tell the one named Buddy that this request is ready to fulfil —
        not the whole central office (CONTEXT.md ▸ Buddy).

        ``sudo`` after the authority check: creating a mail.activity is gated
        on ``_mail_post_access`` applied to the *request* (mail_activity.py
        ``_filter_access_rules_remaining``), i.e. on the OU read rule here, so
        an approver outside the requesting unit's OU could not schedule it.
        Who may approve was already decided by ``action_approve`` / the
        e-Saraban letter; the assignee still has to be able to read the
        request, which Odoo enforces in ``_check_access_assignation``.
        """
        for request in self.filtered("officer_id"):
            request.sudo().activity_schedule(
                FULFIL_ACTIVITY,
                user_id=request.officer_id.id,
                summary=_("จัดสรรงบประมาณตามคำขอ %s") % (request.name or ""),
            )

    def _after_done(self):
        """Clear the Buddy's fulfilment Todo and notify the requester.

        ``sudo`` for the same reason as :meth:`_after_approved` — and because
        clearing someone else's activity is otherwise limited to its creator
        or assignee."""
        self.sudo().activity_feedback([FULFIL_ACTIVITY])
        for request in self:
            request.sudo().activity_schedule(ACK_ACTIVITY, user_id=request.user_id.id)

    def _on_fulfilment_posted(self):
        """Move an approved request to in_progress once central has posted a
        transfer or reserved a commitment against it. Idempotent."""
        self.filtered(lambda r: r.state == "approved").write({"state": "in_progress"})

    def _prepare_transfer_vals(self):
        """Default values for the draft ``budget.transfer`` opened by
        :meth:`action_fulfil_transfer`. ``account_id`` on the destination line is left
        unset — it is a hard required field with no default, so it is filled
        in by central on the (unsaved) form rather than at creation time."""
        self.ensure_one()
        return {
            # No ``move_type``: it is not on the transfer form, so default_get
            # would never be asked for it — and budget.transfer.create already
            # setdefaults it to "entry".
            "reason": html2plaintext(self.reason or ""),
            "date": self.date,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            # แหล่งเงิน IS known and must match on both sides of a transfer
            # (ADR-0009), unlike the department.
            "source_analytic_id": self.source_analytic_id.id,
            # NO header department: on a budget.transfer the header IS the
            # source (FROM lines hide the field and always take it), and a
            # support request is central funding a unit — central picks its
            # own source department here. Only the destination is known.
            "support_request_id": self.id,
            # ``to_line_ids`` — NOT ``line_ids``: the transfer form view only
            # carries the from/to authoring boxes, and ``default_get`` is only
            # asked for fields the view contains.
            "to_line_ids": [
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
            "source_analytic_id": self.source_analytic_id.id,
            "support_request_id": self.id,
        }
