import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, formatLang

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    """Budget Commitment - Ledger-style budget reservation and tracking.

    Workflow: จองงบ (reserve) -> ผูกพัน (obligate) -> ตัดงบ (consume)

    Header holds shared context (department, source, cap amount).
    Lines are ledger entries tracking all budget operations with full audit trail.
    """

    _name = "budget.commitment"
    _description = "Budget Commitment"
    _inherit = ["analytic.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "ref", "title"]

    READONLY_STATES = {
        "reserved": [("readonly", True)],
        "partial": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        string="Number",
        required=True,
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
        readonly=False,
        states=READONLY_STATES,
    )
    title = fields.Char(
        string="ชื่อรายการจอง",
        required=True,
        tracking=True,
        index="trigram",
        readonly=False,
        states=READONLY_STATES,
        help=(
            "ชื่อ/วัตถุประสงค์ของใบจองงบประมาณ แสดงคู่กับเลขที่ใบจองทุกที่ที่ต้องเลือกใบจอง "
            "(เช่น ช่องหยิบใบจองใน พ.1 / ใบขออนุมัติ) — ใบจองที่สร้างจากโครงการหรือ"
            "แผนจัดซื้อจัดจ้างจะเติมชื่อของเอกสารต้นทางให้อัตโนมัติ"
        ),
    )
    ref = fields.Char(
        string="Reference",
        copy=False,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    date = fields.Date(
        string="Commitment Date",
        required=True,
        index=True,
        default=fields.Date.context_today,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("reserved", "Reserved"),
            ("partial", "In Progress"),
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
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    description = fields.Text(
        string="Description",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    user_id = fields.Many2one(
        string="User",
        comodel_name="res.users",
        copy=False,
        default=lambda self: self.env.user,
        store=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )

    # Header amount = user-set cap (วงเงินอนุมัติ)
    amount = fields.Monetary(
        string="วงเงินอนุมัติ",
        required=True,
        currency_field="currency_id",
        tracking=True,
        help="Maximum budget amount for this commitment (cap)",
        states=READONLY_STATES,
    )

    # Primary budget account (header-level default for lines)
    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
        tracking=True,
        states=READONLY_STATES,
    )

    # Header-level analytics: all 4 dimensions (shared default for lines)
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="โครงการ/กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_kmitl_project_analytic",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แผนจัดซื้อจัดจ้าง",
        compute="_compute_analytic_id",
        inverse="_inverse_procurement_plan_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    _analytic_keys = {
        "departments": "department_analytic_id",
        "sources": "source_analytic_id",
        "activities": "activity_analytic_id",
        "funds": "fund_analytic_id",
        "kmitl_project": "kmitl_project_analytic_id",
        "procurement_plan": "procurement_plan_analytic_id",
    }

    def _inverse_department_analytic(self):
        for record in self:
            record._update_analytic_distribution("departments")

    def _inverse_source_analytic(self):
        for record in self:
            record._update_analytic_distribution("sources")

    def _inverse_activity_analytic(self):
        for record in self:
            record._update_analytic_distribution("activities")

    def _inverse_fund_analytic(self):
        for record in self:
            record._update_analytic_distribution("funds")

    def _inverse_kmitl_project_analytic(self):
        for record in self:
            record._update_analytic_distribution("kmitl_project")

    def _inverse_procurement_plan_analytic(self):
        for record in self:
            record._update_analytic_distribution("procurement_plan")

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        states=READONLY_STATES,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        store=True,
    )
    notes = fields.Text(string="Notes")

    # Ledger lines
    line_ids = fields.One2many(
        comodel_name="budget.commitment.line",
        inverse_name="commitment_id",
        string="Ledger Lines",
        copy=True,
    )

    # Computed balances from lines
    total_reserved = fields.Monetary(
        string="ยอดจองงบ",
        compute="_compute_line_totals",
        store=True,
        currency_field="currency_id",
    )
    total_obligated = fields.Monetary(
        string="ยอดผูกพัน",
        compute="_compute_line_totals",
        store=True,
        currency_field="currency_id",
    )
    total_consumed = fields.Monetary(
        string="ยอดตัดงบ",
        compute="_compute_line_totals",
        store=True,
        currency_field="currency_id",
    )
    available_to_obligate = fields.Monetary(
        string="คงเหลือผูกพันได้",
        compute="_compute_line_totals",
        store=True,
        currency_field="currency_id",
    )
    available_to_consume = fields.Monetary(
        string="คงเหลือตัดงบได้",
        compute="_compute_line_totals",
        store=True,
        currency_field="currency_id",
    )

    # Legacy backward-compat fields
    consumed_amount = fields.Monetary(
        string="Consumed Amount",
        compute="_compute_line_totals",
        store=True,
        currency_field="currency_id",
    )
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_line_totals",
        store=True,
        currency_field="currency_id",
    )

    # Cross-year carry-over references
    carried_over_from_id = fields.Many2one(
        "budget.commitment",
        string="Carried Over From",
        readonly=True,
        copy=False,
    )
    carried_over_to_id = fields.Many2one(
        "budget.commitment",
        string="Carried Over To",
        readonly=True,
        copy=False,
    )

    # Related budget moves
    budget_move_ids = fields.One2many(
        comodel_name="budget.move",
        inverse_name="commitment_id",
        string="Related Budget Moves",
        readonly=True,
    )

    @api.depends(
        "line_ids.amount",
        "line_ids.move_type",
        "line_ids.state",
        "amount",
    )
    def _compute_line_totals(self):
        for record in self:
            posted = record.line_ids.filtered(lambda l: l.state == "posted")
            total_reserved = sum(
                posted.filtered(lambda l: l.move_type == "reserve").mapped("amount")
            )
            total_obligated = sum(
                posted.filtered(lambda l: l.move_type == "obligate").mapped("amount")
            )
            total_consumed = sum(
                posted.filtered(lambda l: l.move_type == "consume").mapped("amount")
            )
            record.total_reserved = total_reserved
            record.total_obligated = total_obligated
            record.total_consumed = total_consumed
            record.available_to_obligate = total_reserved - total_obligated
            record.available_to_consume = total_obligated - total_consumed
            # Legacy compat
            record.consumed_amount = total_consumed
            record.remaining_amount = record.amount - total_consumed

    def _sync_state(self):
        """Derive the active band (reserved/partial/done) from line totals.

        Runs only while the commitment is active; draft and cancel are explicit
        user states and are left untouched, so this never fights action_reserve,
        action_cancel or action_reset_to_draft. "done" means the reservation has
        been fully consumed, which keeps multi-installment commitments open until
        the final draw-down.
        """
        for record in self:
            if record.state in ("draft", "cancel"):
                continue
            rounding = record.currency_id.rounding or 0.01
            reserved = record.total_reserved
            consumed = record.total_consumed
            obligated = record.total_obligated
            if (
                float_compare(reserved, 0.0, precision_rounding=rounding) > 0
                and float_compare(consumed, reserved, precision_rounding=rounding) >= 0
            ):
                new_state = "done"
            elif (
                float_compare(obligated, 0.0, precision_rounding=rounding) > 0
                or float_compare(consumed, 0.0, precision_rounding=rounding) > 0
            ):
                new_state = "partial"
            else:
                new_state = "reserved"
            if record.state != new_state:
                record.state = new_state

    @api.constrains("amount", "state")
    def _check_positive_amount(self):
        # A draft is a staging area — a zero วงเงินอนุมัติ is allowed while the
        # slip is being filled in. Reserving requires a positive amount, enforced
        # in action_reserve and re-guarded here for any active commitment. A
        # negative cap is never valid.
        for record in self:
            if record.amount < 0:
                raise UserError(_("Commitment cap amount cannot be negative."))
            if record.state != "draft" and record.amount <= 0:
                raise UserError(_("Commitment cap amount must be positive."))

    # --- Display ---

    def name_get(self):
        """Show ``BC0001 - ชื่อรายการจอง`` instead of the bare number.

        A reservation is picked by *what it is for* (a การจอง for a project, a
        plan, or a unit's support), so every place that offers a commitment —
        the draw-down dropdown on พ.1 / ใบขออนุมัติ above all — must carry the
        title next to the number.
        """
        return [
            (record.id, "%s - %s" % (record.name, record.title))
            if record.title
            else (record.id, record.name)
            for record in self
        ]

    @api.depends("name", "title")
    def _compute_display_name(self):
        # Base depends only on _rec_name (``name``), so editing the title would
        # otherwise leave a stale display_name in cache.
        return super()._compute_display_name()

    def get_reservation_info(self):
        """Display payload for the ``budget_commitment_info`` field widget.

        One dict per record: identity plus label/value rows the widget renders
        verbatim, so labels, translations and money formatting all stay
        server-side and the widget stays dumb. Bridge modules may enrich it by
        overriding :meth:`_reservation_info_rows`; the operating unit is left out
        on purpose (it is the visibility axis, not what a slip is picked by).
        """
        state_labels = dict(self._fields["state"]._description_selection(self.env))
        return [
            {
                "id": record.id,
                "name": record.name,
                "title": record.title or "",
                "state": record.state,
                "state_label": state_labels.get(record.state, record.state),
                "rows": record._reservation_info_rows(),
                "amounts": record._reservation_info_amounts(),
            }
            for record in self
        ]

    # The four financial dimensions are always listed, even when empty: the
    # engine matches all dimensions or pins a missing one to False, so "this
    # reservation has no กองทุน" is information the reader needs, not noise.
    _RESERVATION_INFO_FIELDS = (
        "account_id",
        "department_analytic_id",
        "source_analytic_id",
        "activity_analytic_id",
        "fund_analytic_id",
        "account_fiscal_year_id",
    )
    # โครงการ/แผนจัดซื้อจัดจ้าง are source markers rather than part of every
    # reservation — a standalone slip carries neither — so they are listed only
    # when set, instead of adding two empty rows to the common case.
    _RESERVATION_INFO_FIELDS_IF_SET = (
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
    )

    def _reservation_info_rows(self):
        """Dimension/identity rows shown by the widget (label, value) pairs."""
        self.ensure_one()
        rows = []
        for fname in self._RESERVATION_INFO_FIELDS:
            value = self[fname]
            rows.append(
                {
                    "label": self._fields[fname]._description_string(self.env),
                    "value": value.display_name if value else "-",
                }
            )
        for fname in self._RESERVATION_INFO_FIELDS_IF_SET:
            value = self[fname]
            if value:
                rows.append(
                    {
                        "label": self._fields[fname]._description_string(self.env),
                        "value": value.display_name,
                    }
                )
        return rows

    def _reservation_info_amounts(self):
        """Money rows shown by the widget: just the reservation's own amount.

        Kept as a list so a bridge can still add a figure, but the widget shows
        one by default. The obligated/leftover breakdown belongs on the
        reservation itself — on a consuming document it read as a ledger the
        reader had to interpret, where all they are answering is "is this the
        right slip, and for how much".
        """
        self.ensure_one()
        return [
            {
                "label": _("จำนวนเงิน"),
                "value": formatLang(
                    self.env, self.amount, currency_obj=self.currency_id
                ),
            }
        ]

    # --- Workflow Methods ---

    def action_reserve(self):
        """Draft -> Reserved: synthesize the reserve line from the header and
        check the pool is available.

        The header carries the budget code, dimensions and วงเงินอนุมัติ, so the
        reservation is filled in once on the form — no picker dialog. A zero cap
        is allowed while draft (staging), but reserving requires a positive
        amount.
        """
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft commitments can be reserved."))
            if record.amount <= 0:
                raise UserError(
                    _("กรุณาระบุวงเงินอนุมัติมากกว่า 0 ก่อนจองงบประมาณ")
                )
            if record.total_reserved <= 0:
                record._create_reserve_line_from_header()
            if record.total_reserved <= 0:
                raise UserError(
                    _("Cannot reserve: no reserve lines found. Add reserve lines first.")
                )
            record._check_reserve_availability()
            if record.name == _("New"):
                record.name = self.env["ir.sequence"].next_by_code(
                    "budget.commitment"
                ) or _("New")
            record.state = "reserved"

    def _create_reserve_line_from_header(self):
        """Synthesize the single reserve line from the header (form-first).

        A standalone ใบจอง is filled in once — budget code, dimensions and
        วงเงินอนุมัติ all live on the header — so reserving must not demand the
        same data again through a dialog. Called by :meth:`action_reserve` only
        when no reserve line exists yet, which leaves every programmatic creator
        (project/plan hosts pass ``line_ids`` themselves) untouched.
        """
        self.ensure_one()
        self.write(
            {
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "move_type": "reserve",
                            "account_id": self.account_id.id,
                            "amount": self.amount,
                            "analytic_distribution": self.analytic_distribution,
                            "name": _("Reservation"),
                        },
                    )
                ]
            }
        )

    def _check_reserve_availability(self):
        """Block reserving more than the control-node Available (ADR-0005).

        Runs while the commitment is still ``draft`` (so its own reserve lines are
        not yet counted as ``used``). Skipped when ``budget.allow_negative`` is set.
        Availability is evaluated with the **header** dimension combination
        (``analytic_distribution``) — the reserve lines a host mixin builds carry
        only a subset (activity+fund) while the header carries all dimensions —
        paired with each reserve line's own budget account, so cross-charge lines
        are each checked against their own pool.
        """
        self.ensure_one()
        allow_negative = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        )
        if allow_negative:
            return
        controller = self.env["budget.controller"]
        fy_id = self.account_fiscal_year_id.id
        company_id = self.company_id.id
        rounding = self.currency_id.rounding or 0.01
        avail_distribution = self._availability_distribution()
        reserve_lines = self.line_ids.filtered(
            lambda l: l.state == "posted" and l.move_type == "reserve"
        )
        per_account = {}
        for line in reserve_lines:
            per_account.setdefault(line.account_id, 0.0)
            per_account[line.account_id] += line.amount
        for account, amount in per_account.items():
            available = controller.get_available(
                account, avail_distribution, fy_id, company_id
            )
            if float_compare(available, amount, precision_rounding=rounding) < 0:
                raise UserError(
                    _(
                        "Insufficient budget to reserve %(amount).2f on %(code)s: "
                        "only %(available).2f available at the control node."
                    )
                    % {
                        "amount": amount,
                        "code": account.display_name,
                        "available": available,
                    }
                )

    # kmitl_project rides on the reserve line but the project pool is
    # floating/UNTAGGED (ADR-0007), so availability must be evaluated without it.
    # procurement_plan is NOT stripped: a plan's source appropriation IS tagged
    # with its procurement_plan dimension, so the check must keep the tag to match
    # it (procurement.plan._reserve_plan_commitment carries it in its own
    # pre-check for the same reason).
    _POOL_TAG_PLAN_CODES = ("kmitl_project",)

    def _availability_distribution(self):
        """The dimension combination to evaluate Available against: the header
        distribution with the floating-pool tag (kmitl_project) removed, so a
        project reservation is checked against its floating (untagged)
        appropriation pool — matching kmitl.project._reserve_project_commitment,
        whose pre-check builds analytic_data from the four financial dimensions
        only. Plan (procurement_plan, tagged appropriation) and standalone
        reservations are unchanged."""
        self.ensure_one()
        distribution = dict(self.analytic_distribution or {})
        if not distribution:
            return distribution
        account_ids = [int(k) for k in distribution]
        tag_accounts = self.env["account.analytic.account"].browse(
            account_ids
        ).filtered(
            lambda a: a.root_plan_id and a.root_plan_id.code in self._POOL_TAG_PLAN_CODES
        )
        for acc in tag_accounts:
            distribution.pop(str(acc.id), None)
        return distribution

    def action_done(self):
        """Close the commitment"""
        for record in self:
            if record.state in ("draft", "cancel"):
                raise UserError(
                    _("Cannot close commitment %s from %s state")
                    % (record.name, record.state)
                )
            record.state = "done"
            _logger.info("Closed budget commitment %s", record.name)

    def action_cancel(self):
        """Cancel the commitment and all posted lines"""
        for record in self:
            if record.state == "cancel":
                continue
            if record.state == "done":
                raise UserError(
                    _("Cannot cancel commitment %s - it is already done")
                    % record.name
                )
            record.line_ids.filtered(lambda l: l.state == "posted").action_cancel()
            record.state = "cancel"
            _logger.info("Cancelled budget commitment %s", record.name)

    def action_reset_to_draft(self):
        """Reset cancelled commitment to draft"""
        for record in self:
            if record.state != "cancel":
                raise UserError(
                    _("Only cancelled commitments can be reset to draft.")
                )
            record.state = "draft"

    def action_obligate(self):
        """Open wizard to add an obligate line."""
        self.ensure_one()
        if self.state not in ("reserved", "partial"):
            raise UserError(
                _("Can only obligate in reserved or in-progress state.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("ผูกพันงบประมาณ"),
            "res_model": "budget.commitment.line.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_commitment_id": self.id,
                "default_move_type": "obligate",
            },
        }

    def action_consume(self):
        """Open wizard to add a consume line."""
        self.ensure_one()
        if self.state not in ("reserved", "partial"):
            raise UserError(
                _("Can only consume in reserved or in-progress state.")
            )
        if self.available_to_consume <= 0:
            raise UserError(
                _("No obligated amount available to consume.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("ตัดงบประมาณ"),
            "res_model": "budget.commitment.line.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_commitment_id": self.id,
                "default_move_type": "consume",
            },
        }

    def action_return_leftover(self):
        """Open the confirmation wizard to return leftover reserved budget (คืนจอง).

        The leftover = ``available_to_obligate`` (reserved − obligated, which
        equals reserved − consumed because the KMITL flows post obligate and
        consume together). Confirming posts a single negative ``reserve`` line
        (``is_return=True``) that releases the unspent earmark back to the pool
        without cancelling the commitment (see CONTEXT.md / ADR-0009).
        Reserved/in-progress only.
        """
        self.ensure_one()
        if self.state not in ("reserved", "partial"):
            raise UserError(
                _(
                    "Can only return leftover budget on a reserved or "
                    "in-progress commitment."
                )
            )
        return self._action_return_leftover_wizard()

    def _action_return_leftover_wizard(self, res_model=False, res_id=False):
        """Build the act_window that opens the return-leftover (คืนจอง) wizard.

        Shared by the commitment button and the disbursement-request shortcut so
        the wizard model, the label and the "no leftover" guard live in one
        place. ``res_model``/``res_id`` stamp the initiating document on the
        posted return line for drill-down traceability.
        """
        self.ensure_one()
        if self.available_to_obligate <= 0:
            raise UserError(_("No leftover reserved budget to return."))
        context = {"default_commitment_id": self.id}
        if res_model:
            context["default_res_model"] = res_model
        if res_id:
            context["default_res_id"] = res_id
        return {
            "type": "ir.actions.act_window",
            "name": _("ส่งคืนเงินเหลือจ่าย"),
            "res_model": "budget.commitment.return.wizard",
            "view_mode": "form",
            "target": "new",
            "context": context,
        }

    def action_view_budget_moves(self):
        """View related budget moves"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Related Budget Moves"),
            "res_model": "budget.move",
            "view_mode": "tree,form",
            "domain": [("commitment_id", "=", self.id)],
            "context": {"default_commitment_id": self.id},
        }

    # The reservation picker (amounts mode) on the commitment itself is gone:
    # the core journey is form-first — the header IS the single reserve line
    # (see _create_reserve_line_from_header). The picker JS component stays as
    # shared infrastructure for the select-only hosts (พ.1 / ใบขออนุมัติ).
