import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, formatLang

_logger = logging.getLogger(__name__)

_BUCKETS = ("reserve", "obligate", "consume")
_TOTAL_FIELDS = (
    "total_reserved",
    "total_obligated",
    "total_consumed",
    "available_to_obligate",
    "available_to_consume",
)


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
        states={"cancel": [("readonly", True)]},
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

    # Commitment events — commands posted to the budget ledger, never summed
    line_ids = fields.One2many(
        comodel_name="budget.commitment.line",
        inverse_name="commitment_id",
        string="เหตุการณ์ใบจอง",
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
    # The reservation's sub-ledger in the budget ledger (ADR-0016): every
    # figure below is read from these lines, never from line_ids.
    ledger_line_ids = fields.One2many(
        comodel_name="budget.move.line",
        inverse_name="commitment_id",
        string="บัญชีงบประมาณ",
        readonly=True,
    )

    @api.depends(
        "ledger_line_ids.balance",
        "ledger_line_ids.move_type",
        "ledger_line_ids.parent_state",
        "amount",
    )
    def _compute_line_totals(self):
        """The negated Σ balance of the posted ledger lines per bucket
        (ADR-0016): b = reserve, c = obligate, d = consume.
        ``available_to_obligate`` = b, ``available_to_consume`` = c,
        ``total_consumed`` = d, ``total_obligated`` = c + d and
        ``total_reserved`` = b + c + d."""
        sums = self._ledger_bucket_sums()
        for record in self:
            buckets = sums.get(record._origin.id) or dict.fromkeys(_BUCKETS, 0.0)
            reserve, obligate, consume = (-buckets[b] for b in _BUCKETS)
            record.available_to_obligate = reserve
            record.available_to_consume = obligate
            record.total_consumed = consume
            record.total_obligated = obligate + consume
            record.total_reserved = reserve + obligate + consume

    def _ledger_bucket_sums(self):
        """{commitment id: {bucket: Σ posted balance}} of these reservations'
        ledger lines, in one grouped query instead of a Python loop over every
        line on each recompute."""
        ids = self._origin.ids
        sums = {cid: dict.fromkeys(_BUCKETS, 0.0) for cid in ids}
        if not ids:
            return sums
        groups = (
            self.env["budget.move.line"]
            .sudo()
            .read_group(
                [
                    ("commitment_id", "in", ids),
                    ("parent_state", "=", "posted"),
                    ("move_type", "in", list(_BUCKETS)),
                ],
                ["balance:sum"],
                ["commitment_id", "move_type"],
                lazy=False,
            )
        )
        for group in groups:
            sums[group["commitment_id"][0]][group["move_type"]] += (
                group["balance"] or 0.0
            )
        for record in self._origin:
            currency = record.currency_id or self.env.company.currency_id
            sums[record.id] = {
                key: currency.round(value) for key, value in sums[record.id].items()
            }
        return sums

    def _ledger_buckets(self):
        """{bucket: Σ posted balance} of this reservation's ledger lines."""
        self.ensure_one()
        return self._ledger_bucket_sums().get(self._origin.id) or dict.fromkeys(
            _BUCKETS, 0.0
        )

    def _ledger_codes(self):
        """The reservation's budget codes in liquidation order (ADR-0017): the
        header's primary code first, then each other reserved code (ถัวจ่าย) in
        the order it was added."""
        self.ensure_one()
        codes = self.account_id
        for line in self.line_ids:
            if (
                line.move_type == "reserve"
                and line.state == "posted"
                and not line.is_return
            ):
                codes |= line.account_id
        return codes

    def _ledger_unobligated(self, account):
        """What ``account``'s code still holds reserved and unobligated (b).
        Read as sudo: the operating-unit rules must not hide part of a
        reservation's own ledger from the figure."""
        self.ensure_one()
        groups = (
            self.env["budget.move.line"]
            .sudo()
            .read_group(
                [
                    ("commitment_id", "=", self.id),
                    ("parent_state", "=", "posted"),
                    ("move_type", "=", "reserve"),
                    ("account_id", "=", account.id),
                ],
                ["balance:sum"],
                [],
            )
        )
        return -((groups[0]["balance"] or 0.0) if groups else 0.0)

    def _ledger_default_consume(self):
        """What a consume with no amount takes: the open obligation, or — when
        nothing is obligated — the unobligated reserve it then liquidates."""
        self.ensure_one()
        return self.available_to_consume or self.available_to_obligate

    def _check_ledger_limits(self):
        """reserved ≤ cap, and no bucket overdrawn — read from the ledger."""
        for commitment in self:
            rounding = commitment.currency_id.rounding or 0.01

            def over(a, b):
                return float_compare(a, b, precision_rounding=rounding) > 0

            reserved = commitment.total_reserved
            obligated = commitment.total_obligated
            consumed = commitment.total_consumed
            if commitment.amount and over(reserved, commitment.amount):
                raise ValidationError(
                    _(
                        "Total reserved (%(reserved).2f) exceeds commitment cap (%(cap).2f)"
                    )
                    % {"reserved": reserved, "cap": commitment.amount}
                )
            if over(obligated, reserved):
                raise ValidationError(
                    _(
                        "Total obligated (%(obligated).2f) exceeds total reserved (%(reserved).2f)"
                    )
                    % {"obligated": obligated, "reserved": reserved}
                )
            if over(consumed, obligated):
                raise ValidationError(
                    _(
                        "Total consumed (%(consumed).2f) exceeds total obligated (%(obligated).2f)"
                    )
                    % {"consumed": consumed, "obligated": obligated}
                )
            for label, value in (
                (_("reserved"), reserved),
                (_("obligated"), obligated),
                (_("consumed"), consumed),
            ):
                if over(0.0, value):
                    raise ValidationError(
                        _("Total %(label)s cannot be negative (%(value).2f).")
                        % {"label": label, "value": value}
                    )

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
            # The pending reserve events are the command to reserve (they post to
            # the ledger only once reserved), so test for them, not for a total.
            if not record._pending_reserve_lines():
                record._create_reserve_line_from_header()
            if sum(record._pending_reserve_lines().mapped("amount")) <= 0:
                raise UserError(
                    _("Cannot reserve: no reserve lines found. Add reserve lines first.")
                )
            record._check_reserve_availability()
            if record.name == _("New"):
                record.name = self.env["ir.sequence"].next_by_code(
                    "budget.commitment"
                ) or _("New")
            record.state = "reserved"
            # Post now, before the next one in a batch is checked: the pool
            # only nets a reservation once its events are in the ledger.
            record._pending_reserve_lines()._post_budget_moves()

    def _create_reserve_line_from_header(self):
        """Synthesize the single reserve line from the header (form-first).

        A standalone ใบจอง is filled in once — budget code, dimensions and
        วงเงินอนุมัติ all live on the header — so reserving must not demand the
        same data again through a dialog. Called by :meth:`action_reserve` only
        when no reserve line exists yet, which leaves every programmatic creator
        (project/plan hosts pass ``line_ids`` themselves) untouched.
        """
        self.ensure_one()
        self._post_budget_event("reserve", self.amount, name=_("Reservation"))

    def _pending_reserve_lines(self):
        """The posted reserve events of a reservation (its reserve command)."""
        self.ensure_one()
        return self.line_ids.filtered(
            lambda l: l.state == "posted" and l.move_type == "reserve"
        )

    # --- Event seam (ADR-0016) ---
    #
    # Every write to a reservation goes through these three methods instead of
    # ``budget.commitment.line.create`` / filtering ``line_ids``, so each event
    # is posted to the budget ledger and read back from it in one place.

    def _get_budget_event_target(self, move_type, is_return=False):
        """(budget.account, analytic_distribution) an event posts against.

        A reservation is posted on the header; every later event (a return
        included) lands on the first posted reserve line, the convention the
        consume flows have always used, so it nets at the original control node
        (ADR-0009).
        """
        self.ensure_one()
        if move_type != "reserve" or is_return:
            first_reserve = self.line_ids.filtered(
                lambda l: l.move_type == "reserve"
                and l.state == "posted"
                and not l.is_return
            )[:1]
            if not first_reserve:
                raise UserError(
                    _("No active reserve line on commitment %s.") % self.name
                )
            return first_reserve.account_id, first_reserve.analytic_distribution
        return self.account_id, self.analytic_distribution

    def _prepare_budget_event_vals(
        self, move_type, amount, source=None, name=None, is_return=False, date=None
    ):
        self.ensure_one()
        account, distribution = self._get_budget_event_target(
            move_type, is_return=is_return
        )
        vals = {
            "commitment_id": self.id,
            "move_type": move_type,
            "account_id": account.id,
            "analytic_distribution": distribution,
            "amount": amount,
            "is_return": is_return,
            "name": name,
        }
        if date:
            vals["date"] = date
        if source:
            vals["res_model"] = source._name
            vals["res_id"] = source.id
        return vals

    def _post_budget_event(
        self, move_type, amount, *, source=None, name=None, is_return=False, date=None
    ):
        """Record one event (reserve / obligate / consume / return) on this
        reservation and return its ``budget.commitment.line``.

        ``source`` is the document that caused the event (stamped as
        ``res_model``/``res_id`` so the event can be found and undone per
        document); a return is a negative ``reserve`` with ``is_return``.
        """
        self.ensure_one()
        return self.env["budget.commitment.line"].create(
            self._prepare_budget_event_vals(
                move_type,
                amount,
                source=source,
                name=name,
                is_return=is_return,
                date=date,
            )
        )

    def _budget_event_lines(self, source=None, move_types=None):
        """The posted events of this reservation, optionally of one source
        document and/or some types — read from the ledger: each live event
        owns one posted primary ledger line, in its own move or inside a
        transfer's move for a top-up/release."""
        self.ensure_one()
        domain = [
            ("commitment_id", "=", self.id),
            ("parent_state", "=", "posted"),
            ("is_liquidation", "=", False),
            ("commitment_line_id.state", "=", "posted"),
        ]
        if source:
            domain += [
                ("commitment_line_id.res_model", "=", source._name),
                ("commitment_line_id.res_id", "=", source.id),
            ]
        if move_types:
            domain.append(("commitment_line_id.move_type", "in", list(move_types)))
        lines = self.env["budget.move.line"].sudo().search(domain)
        return lines.commitment_line_id.with_env(self.env)

    def _has_budget_event(self, source, move_type):
        """Whether ``source`` already has a posted ``move_type`` event here."""
        self.ensure_one()
        return bool(self._budget_event_lines(source=source, move_types=(move_type,)))

    def _cancel_budget_events(self, source=None, move_types=None):
        """Cancel the posted events of ``source`` (all when omitted), leaving
        other documents' draws on a shared reservation untouched."""
        self.ensure_one()
        self._budget_event_lines(source=source, move_types=move_types).action_cancel()
        return True

    def _check_reserve_availability(self):
        """Block reserving more than the control-node Available (ADR-0005).

        Runs while the commitment is still ``draft`` (so its own reserve lines are
        not yet in the ledger). Skipped when ``budget.allow_negative`` is set.
        Availability is evaluated with the **header** dimension combination
        (``analytic_distribution``) — the reserve lines a host mixin builds carry
        only a subset (activity+fund) while the header carries all dimensions —
        paired with each reserve line's own budget account.

        The amounts are summed **per control node**, not per budget code: the
        codes of a ถัวจ่าย reservation that resolve to the same funded ancestor
        draw on one pool, so each must not be checked against the whole of it
        on its own.
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
        dims = controller._parse_dimensions(self._availability_distribution())
        pools = {}  # control-node key -> [controls, amount, accounts]
        for line in self._pending_reserve_lines():
            controls = controller._resolve_control_nodes(
                line.account_id, dims, fy_id, company_id
            )
            key = (
                controls["account"].id,
                tuple(sorted((col, rec.id) for col, rec in controls["dims"].items())),
            )
            pool = pools.setdefault(
                key, [controls, 0.0, self.env["budget.account"]]
            )
            pool[1] += line.amount
            pool[2] |= line.account_id
        for controls, amount, accounts in pools.values():
            available = controller._sum_available(controls, dims, fy_id, company_id)
            if float_compare(available, amount, precision_rounding=rounding) < 0:
                raise UserError(
                    _(
                        "Insufficient budget to reserve %(amount).2f on %(code)s: "
                        "only %(available).2f available at the control node."
                    )
                    % {
                        "amount": amount,
                        "code": ", ".join(accounts.mapped("display_name")),
                        "available": available,
                    }
                )

    def _availability_distribution(self):
        """Pool tags are pinned on both sides of the engine (ADR-0016, Q3), so a
        reservation is checked at its full coordinate, tag included."""
        self.ensure_one()
        return dict(self.analytic_distribution or {})

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
            # Every move carrying this reservation's ledger lines — its own
            # event moves and the transfers that topped it up.
            "domain": [("id", "in", self.ledger_line_ids.move_id.ids)],
            # Event moves are posted by the reservation itself, never by hand.
            "context": {"create": False},
        }

    # The reservation picker (amounts mode) on the commitment itself is gone:
    # the core journey is form-first — the header IS the single reserve line
    # (see _create_reserve_line_from_header). The picker JS component stays as
    # shared infrastructure for the select-only hosts (พ.1 / ใบขออนุมัติ).

    # ------------------------------------------------------------------
    # Back-fill + reconciliation (ADR-0016, Q11)
    # ------------------------------------------------------------------
    def _ledger_legacy_totals(self):
        """(reserved, obligated, consumed) re-derived from the posted events the
        old way, for reconciliation only — never used as a figure."""
        self.ensure_one()
        sums = dict.fromkeys(_BUCKETS, 0.0)
        for line in self.line_ids.filtered(lambda line: line.state == "posted"):
            sums[line.move_type] += line.amount
        # The old ledger forbade consuming more than obligated; a consume that
        # liquidated the reserve directly counts as obligated too.
        return sums["reserve"], max(sums["obligate"], sums["consume"]), sums["consume"]

    def _ledger_mismatches(self):
        """Reservations whose ledger figures differ from their posted events,
        or whose pool-tag coordinate is over-committed (see
        :meth:`_ledger_tag_shortfall`)."""
        mismatched = self.browse()
        for commitment in self:
            rounding = commitment.currency_id.rounding or 0.01
            legacy = commitment._ledger_legacy_totals()
            ledger = (
                commitment.total_reserved,
                commitment.total_obligated,
                commitment.total_consumed,
            )
            if any(
                float_compare(a, b, precision_rounding=rounding)
                for a, b in zip(legacy, ledger)
            ) or commitment._ledger_tag_shortfall():
                mismatched |= commitment
        return mismatched

    def _ledger_tag_shortfall(self):
        """How far an active reservation's own pool-tag coordinate (โครงการ /
        แผนจัดซื้อจัดจ้าง) is over-committed — 0.0 when it is covered or the
        reservation carries no tag.

        The pool tags are pinned on both sides (ADR-0016, Q3), so a tagged
        reservation is only covered by money at its tagged coordinate. One made
        against the untagged floating pool (ADR-0007, before the money was
        transferred onto the tag) leaves that coordinate negative and frees its
        amount back on the untagged pool — the per-coordinate comparison cannot
        see it, so it is reported here."""
        self.ensure_one()
        if self.state not in ("reserved", "partial", "done") or not (
            self.kmitl_project_analytic_id or self.procurement_plan_analytic_id
        ):
            return 0.0
        available = (
            self.env["budget.controller"]
            .sudo()
            .get_available(
                self.account_id,
                self._availability_distribution(),
                self.account_fiscal_year_id.id,
                self.company_id.id,
            )
        )
        rounding = self.currency_id.rounding or 0.01
        if float_compare(available, 0.0, precision_rounding=rounding) < 0:
            return -available
        return 0.0

    def _ledger_backfill(self):
        """Post the history of every active reservation to the ledger.

        Per reservation, its posted events are posted in date order; an event
        that already has its consume move keeps it and gains the liquidation
        lines. Mismatches are logged and kept in
        ``budget.ledger_backfill_mismatch_commitment_ids`` — the upgrade never
        aborts on them (ADR-0016, Q11).
        """
        everything = self.search([])
        # The stored figures still hold the event-based values; recompute them
        # from the ledger as it fills, so each consume liquidates the right bucket.
        for fname in _TOTAL_FIELDS:
            self.env.add_to_compute(self._fields[fname], everything)
        commitments = everything.filtered(
            lambda c: c.state not in ("draft", "cancel")
        ).sorted("id")
        for commitment in commitments:
            events = commitment.line_ids.filtered(
                lambda line: line.state == "posted" and not line.budget_move_line_id
            ).sorted(lambda line: (line.date, line.id))
            for event in events:
                try:
                    with self.env.cr.savepoint():
                        event._ledger_backfill_post()
                except Exception as err:  # report, never abort the upgrade
                    _logger.warning(
                        "budget ledger back-fill: event %s of %s not posted: %s",
                        event.id,
                        commitment.display_name,
                        err,
                    )
        for fname in _TOTAL_FIELDS:
            self.env.add_to_compute(self._fields[fname], everything)
        everything.flush_recordset()
        mismatched = commitments._ledger_mismatches()
        if mismatched:
            _logger.warning(
                "budget ledger back-fill: %d reservation(s) do not reconcile: %s",
                len(mismatched),
                ", ".join(mismatched.mapped("display_name")),
            )
        else:
            _logger.info(
                "budget ledger back-fill: %d reservation(s) posted and reconciled",
                len(commitments),
            )
        self.env["ir.config_parameter"].sudo().set_param(
            "budget.ledger_backfill_mismatch_commitment_ids",
            json.dumps(mismatched.ids),
        )
        return mismatched
