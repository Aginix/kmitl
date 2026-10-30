import logging

from odoo.tools import float_compare, float_is_zero
from odoo.tools.misc import format_amount
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    # This layer gives ``to_verify`` its budget meaning — the plan waits here for
    # งานแผน to allocate budget (ปรับเข้าแผน) and then reserves it (จองงบ) — so
    # relabel the state to match. ``selection_add`` on an existing key overrides
    # its label only (no new value, no ondelete needed).
    state = fields.Selection(
        selection_add=[
            ("to_verify", "รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจองงบประมาณ"),
        ],
    )

    budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        tracking=True,
        domain="[('procurement_plan', '=', True), ('budgetable', '=', True), ('budget_type', '=', 'expense')]",
        states={
            "to_verify": [("readonly", True)],
            "in_progress": [("readonly", True)],
            "done": [("readonly", True)],
            "cancel": [("readonly", True)],
        },
    )

    budget_commitment_ids = fields.One2many(
        "budget.commitment",
        "procurement_plan_id",
        string="ผูกพันงบประมาณ",
        readonly=True,
        # Duplicating a plan copies its dimensions (มิติบัญชี) but must start with
        # a clean reservation — the ใบจอง belongs to the original plan only.
        copy=False,
    )
    budget_commitment_count = fields.Integer(
        string="จำนวนผูกพันงบประมาณ", compute="_compute_budget_commitment_count"
    )

    budget_amount = fields.Float(
        string="งบประมาณที่ได้รับการจัดสรร",
        digits="Product Price",
        compute="_compute_budget_amount",
        help="งบประมาณที่ได้รับจัดสรรจริง คำนวณจากยอดโอนเข้า-ออก (budget.move.line) "
        "ที่ตรงกับรหัสงบและมิติทั้งหมดของแผน (รวมมิติแผนจัดซื้อจัดจ้าง)",
    )

    budget_move_line_count = fields.Integer(
        string="รายการเคลื่อนไหวงบ",
        compute="_compute_budget_move_line_count",
    )
    # Read from the ledger, which plan users cannot read: compute as sudo.
    budget_consumed = fields.Float(
        string="เบิกจ่ายแล้ว",
        digits="Product Price",
        compute="_compute_budget_remaining",
        compute_sudo=True,
        help="ยอดตัดงบ (เบิกจ่าย) ที่ผ่านแล้ว ณ รหัสงบและมิติทั้งหมดของแผน",
    )
    budget_remaining = fields.Float(
        string="งบประมาณคงเหลือ",
        digits="Product Price",
        compute="_compute_budget_remaining",
        compute_sudo=True,
        help="งบประมาณที่ได้รับการจัดสรร หักด้วยยอดที่เบิกจ่ายไปแล้ว (เงินที่ยังอยู่ในแผน)",
    )
    budget_short = fields.Boolean(
        compute="_compute_budget_short",
        help="ได้รับงบประมาณแล้วแต่ยังไม่ครบวงเงินตามแผน จึงยังจองงบไม่ได้",
    )
    has_held_money = fields.Boolean(
        string="มีเงินค้างในมิติแผน",
        compute="_compute_has_held_money",
        search="_search_has_held_money",
        help="ยังมียอดจัดสรรสุทธิค้างอยู่ในมิติแผน (ทุกพิกัด ทุกปีงบประมาณ) "
        "ต้องโอนคืนงบลอยก่อนจึงจะลบแผนหรือเปลี่ยนรหัสงบ/มิติได้",
    )

    def _compute_budget_commitment_count(self):
        for rec in self:
            rec.budget_commitment_count = len(rec.budget_commitment_ids)

    @api.depends(
        "analytic_account_id",
        "analytic_distribution",
        "budget_account_id",
        "account_fiscal_year_id",
        "company_id",
    )
    def _compute_budget_amount(self):
        """Current Budget at the plan's **full target coordinate**: Σ posted
        appropriation/entry balance on budget.move.line matching the plan's
        รหัสงบ (``budget_account_id``) + every budget dimension (the four base
        dims + the plan's own ``procurement_plan`` dim). Scopes to the same
        coordinate as the reserve availability check. Reads 0 before งานแผน
        transfers budget in (ปรับเข้าแผน), which is what gates จองงบ."""
        BML = self.env["budget.move.line"]
        _APPROPRIATION_TYPES = ("appropriation", "entry")
        for rec in self:
            if (
                not rec.analytic_account_id
                or not rec.account_fiscal_year_id
                or not rec.budget_account_id
            ):
                rec.budget_amount = 0.0
                continue
            domain = rec._budget_coordinate_domain() + [
                ("move_type", "in", list(_APPROPRIATION_TYPES)),
            ]
            groups = BML.read_group(domain, ["balance"], [])
            rec.budget_amount = (groups[0].get("balance") or 0.0) if groups else 0.0

    def _budget_coordinate_domain(self):
        """Posted budget.move.line at the plan's full coordinate: รหัสงบ, fiscal
        year and every budget dimension, its own plan dimension included."""
        self.ensure_one()
        return [
            ("parent_state", "=", "posted"),
            ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
            ("company_id", "=", self.company_id.id),
            ("account_id", "=", self.budget_account_id.id),
            ("procurement_plan_analytic_id", "=", self.analytic_account_id.id),
            ("department_analytic_id", "=", self.department_analytic_id.id),
            ("fund_analytic_id", "=", self.fund_analytic_id.id),
            ("source_analytic_id", "=", self.source_analytic_id.id),
            ("activity_analytic_id", "=", self.activity_analytic_id.id),
        ]

    @api.depends("budget_amount")
    def _compute_budget_remaining(self):
        """Money still at the plan = Plan Budget − posted ตัดงบ at the same
        coordinate (Plan Budget Remaining)."""
        BML = self.env["budget.move.line"]
        for rec in self:
            consumed = 0.0
            if (
                rec.analytic_account_id
                and rec.account_fiscal_year_id
                and rec.budget_account_id
            ):
                groups = BML.read_group(
                    rec._budget_coordinate_domain() + [("move_type", "=", "consume")],
                    ["balance"],
                    [],
                )
                # Consume lines post a negative balance.
                consumed = -(groups[0].get("balance") or 0.0) if groups else 0.0
            rec.budget_consumed = consumed
            rec.budget_remaining = rec.budget_amount - consumed

    @api.depends("budget_amount", "total_price")
    def _compute_budget_short(self):
        for rec in self:
            rec.budget_short = 0 < rec.budget_amount < rec.total_price

    def _compute_budget_move_line_count(self):
        BML = self.env["budget.move.line"]
        for rec in self:
            if not rec.analytic_account_id:
                rec.budget_move_line_count = 0
                continue
            rec.budget_move_line_count = BML.search_count(
                [
                    ("procurement_plan_analytic_id", "=", rec.analytic_account_id.id),
                    ("account_fiscal_year_id", "=", rec.account_fiscal_year_id.id),
                ]
            )

    def action_open_budget_move_lines(self):
        self.ensure_one()
        return {
            "name": _("รายการเคลื่อนไหวงบประมาณ"),
            "type": "ir.actions.act_window",
            "res_model": "budget.move.line",
            "view_mode": "tree,form",
            "domain": [
                "&",
                ("procurement_plan_analytic_id", "=", self.analytic_account_id.id),
                ("procurement_plan_analytic_id", "!=", False),
                ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
            ],
        }

    def action_view_budget_commitment(self):
        self.ensure_one()
        action = (
            self.env.ref(
                "procurement_plan_budget.action_budget_commitment_procurement_plan"
            )
            .sudo()
            .read()[0]
        )
        action["domain"] = [("procurement_plan_id", "=", self.id)]
        action["context"] = {"default_procurement_plan_id": self.id}
        return action

    def action_open_budget_commitments(self):
        self.ensure_one()
        return {
            "name": "Budget Commitments",
            "type": "ir.actions.act_window",
            "res_model": "budget.commitment",
            "view_mode": "tree,form",
            "domain": [("procurement_plan_id", "=", self.id)],
        }

    def _on_verify(self):
        self._reserve_plan_commitment()

    def _on_reset(self):
        self._release_plan_commitment()

    def _on_cancel(self):
        self._release_plan_commitment()

    def _reserve_plan_commitment(self):
        """Reserve one shared budget.commitment for the plan when it is
        verified (จองงบ), sized to its Plan Budget — what it received — and only
        once that covers its Plan Amount (ADR-0003). Idempotent: skips when an
        active commitment already exists. Downstream PR/PO/DR draw it down."""
        self.ensure_one()
        if self.budget_commitment_ids.filtered(lambda c: c.state != "cancel"):
            return
        if not self.budget_account_id:
            raise UserError(_("กรุณาระบุรหัสงบประมาณก่อนจองงบประมาณ"))
        if self.total_price <= 0:
            raise UserError(_("กรุณาระบุวงเงินรวมให้มากกว่า 0 ก่อนจองงบประมาณ"))
        self.invalidate_recordset(["budget_amount"])
        if self.budget_amount <= 0:
            raise UserError(
                _(
                    "ยังไม่ได้รับการจัดสรรงบประมาณ กรุณารอให้งานแผนโอนงบเข้าแผน "
                    "(ปรับเข้าแผน) ก่อนจึงจะจองงบประมาณได้"
                )
            )
        if float_compare(self.budget_amount, self.total_price, precision_digits=2) < 0:
            raise UserError(
                _(
                    "แผนได้รับงบประมาณ %(received)s ยังไม่ครบวงเงินตามแผน %(planned)s "
                    "กรุณารอให้งานแผนโอนงบเข้าแผนให้ครบก่อนจึงจะจองงบประมาณได้"
                )
                % {
                    "received": format_amount(
                        self.env, self.budget_amount, self.currency_id
                    ),
                    "planned": format_amount(
                        self.env, self.total_price, self.currency_id
                    ),
                }
            )
        analytic_data = {
            "account_id": self.budget_account_id.id,
            "activity_analytic_id": self.activity_analytic_id.id or False,
            "department_analytic_id": self.department_analytic_id.id or False,
            "fund_analytic_id": self.fund_analytic_id.id or False,
            "source_analytic_id": self.source_analytic_id.id or False,
            # The source appropriation is tagged with this plan's own
            # procurement_plan dimension; the check must carry it too, otherwise
            # the engine pins procurement_plan empty and excludes the very
            # appropriation being drawn from (→ false "insufficient budget").
            "procurement_plan_analytic_id": self.analytic_account_id.id or False,
        }
        allow_negative = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        )
        if not allow_negative:
            self.env["budget.controller"].check_budget_availability(
                analytic_data,
                self.budget_amount,
                self.account_fiscal_year_id.id,
                self.company_id.id,
            )
        commitment = self.env["budget.commitment"].create(
            self._prepare_plan_commitment_vals()
        )
        commitment.action_reserve()
        self.message_post(
            body=_("จองงบประมาณ %s จำนวน %s")
            % (
                commitment.name,
                format_amount(self.env, self.budget_amount, self.currency_id),
            )
        )

    def _prepare_plan_commitment_vals(self):
        """Build the create vals for the plan's shared reservation commitment.
        Split out of ``_reserve_plan_commitment`` so bridge modules can enrich the
        commitment — e.g. stamp the plan's operating unit so the reservation lands
        in the same OU as the plan/appropriation — without re-implementing the
        whole reservation flow."""
        self.ensure_one()
        dist = dict(self.analytic_distribution or {})
        return {
            "account_id": self.budget_account_id.id,
            "amount": self.budget_amount,
            "analytic_distribution": dist or False,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "company_id": self.company_id.id,
            "date": fields.Date.context_today(self),
            "ref": self.name,
            # ชื่อรายการของแผน = ชื่อใบจอง (budget.commitment._rec_name shows it
            # next to the number, so a drawing document can tell reservations apart).
            "title": "[%s] %s" % (self.name, self.description)
            if self.name
            else self.description,
            "description": self.description,
            "procurement_plan_id": self.id,
            "user_id": self.env.user.id,
        }

    def _release_plan_commitment(self):
        """Release the plan's reservation when it leaves the active band
        (reset to draft / cancel). Cancels the commitment only while it is still
        untouched AND usage has not started; once the plan is in progress (a
        downstream document has linked the reservation) or any obligate/consume
        draw-down exists, the commitment is kept and a note is posted so in-flight
        spending is never stranded."""
        for plan in self:
            in_use = plan.state == "in_progress"
            for commitment in plan.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            ):
                if in_use or commitment.total_obligated or commitment.total_consumed:
                    plan.message_post(
                        body=_("งบประมาณที่จองไว้ (%s) มีการใช้งานแล้ว จึงไม่ยกเลิกการจอง")
                        % commitment.name
                    )
                    continue
                commitment.action_cancel()
                plan.message_post(body=_("ยกเลิกการจองงบประมาณ %s") % commitment.name)

    # ------------------------------------------------------------------
    # Held Money / Close / Delete (ADR-0005)
    # ------------------------------------------------------------------
    def write(self, vals):
        # Money at the old target would be stranded there (Held Money).
        for plan in self:
            if not plan._is_budget_target_change(vals):
                continue
            reasons = plan._get_held_money_reasons(
                target=(
                    vals.get("budget_account_id", plan.budget_account_id.id),
                    vals["analytic_distribution"]
                    if "analytic_distribution" in vals
                    else plan.analytic_distribution,
                )
            )
            if reasons:
                raise UserError(
                    _(
                        "ไม่สามารถเปลี่ยนรหัสงบประมาณ/มิติงบประมาณของแผน %s ได้ เนื่องจาก:\n%s\n"
                        "กรุณาโอนคืนงบลอยก่อน แล้วจึงแก้ไขและจัดสรรงบประมาณใหม่"
                    )
                    % (plan.name, "\n".join("- %s" % reason for reason in reasons))
                )
        return super().write(vals)

    def _is_budget_target_change(self, vals):
        """Whether ``vals`` changes the budget target: the รหัสงบ or any budget
        dimension other than the plan's own ``procurement_plan`` key."""
        self.ensure_one()
        if not self.analytic_account_id:
            return False
        if (
            "budget_account_id" in vals
            and self.budget_account_id.id != vals["budget_account_id"]
        ):
            return True
        if "analytic_distribution" not in vals:
            return False
        own = str(self.analytic_account_id.id)
        old_dist = self.analytic_distribution or {}
        new_dist = vals["analytic_distribution"] or {}
        return any(
            old_dist.get(k) != new_dist.get(k)
            for k in set(old_dist) | set(new_dist)
            if k != own
        )

    def _plan_ledger_sum(self, move_types):
        """Σ posted ``balance`` at the plan's dimension over ``move_types``, on
        every coordinate and fiscal year."""
        self.ensure_one()
        if not self.analytic_account_id:
            return 0.0
        groups = (
            self.env["budget.move.line"]
            .sudo()
            .read_group(
                [
                    ("parent_state", "=", "posted"),
                    ("move_type", "in", list(move_types)),
                    ("procurement_plan_analytic_id", "=", self.analytic_account_id.id),
                ],
                ["balance"],
                [],
            )
        )
        return (groups[0].get("balance") or 0.0) if groups else 0.0

    def _has_spent(self):
        """Any net obligated/consumed money at the plan's dimension."""
        return super()._has_spent() or not float_is_zero(
            self._plan_ledger_sum(("obligate", "consume")), precision_digits=2
        )

    def _held_outside_target(self, account_id, distribution):
        """Σ the net allocation at the plan's dimension that sits anywhere but
        the coordinate ``account_id`` + ``distribution``'s budget dimensions."""
        self.ensure_one()
        own = str(self.analytic_account_id.id)
        target = set(distribution or {}) - {own}
        lines = (
            self.env["budget.move.line"]
            .sudo()
            .search(
                [
                    ("parent_state", "=", "posted"),
                    ("move_type", "in", ["appropriation", "entry"]),
                    ("procurement_plan_analytic_id", "=", self.analytic_account_id.id),
                ]
            )
        )
        return sum(
            line.balance
            for line in lines
            if line.account_id.id != account_id
            or set(line.analytic_distribution or {}) - {own} != target
        )

    def _get_held_money_reasons(self, target=None):
        """What makes the plan hold money (Held Money): a net allocation on any
        coordinate/fiscal year — wider than ``budget_amount``, which reads only
        the plan's own coordinate — an unspent reservation, or a transfer still
        on its way. Empty when it holds none.

        With ``target`` (``(budget_account_id, analytic_distribution)``) only the
        allocation outside that coordinate counts: retargeting onto where the
        money already sits strands nothing."""
        self.ensure_one()
        reasons = super()._get_held_money_reasons()
        if not self.analytic_account_id:
            return reasons
        if target:
            held = self._held_outside_target(*target)
        else:
            held = self._plan_ledger_sum(("appropriation", "entry"))
        if not float_is_zero(held, precision_digits=2):
            reason = _("มีงบประมาณค้างในมิติแผน %s บาท") % "{:,.2f}".format(held)
            if not target:
                # Only the plan's own coordinate can be returned from.
                stray = self._held_outside_target(
                    self.budget_account_id.id, self.analytic_distribution
                )
                if not float_is_zero(stray, precision_digits=2):
                    reason += _(
                        " (ในจำนวนนี้ %s บาท อยู่ที่รหัสงบประมาณ/มิติเดิมของแผน "
                        "กรุณาแก้รหัสงบประมาณ/มิติกลับให้ตรงกับที่เงินอยู่ก่อนโอนคืนงบลอย)"
                    ) % "{:,.2f}".format(stray)
            reasons.append(reason)
        reserved = sum(
            self.sudo()
            .budget_commitment_ids.filtered(lambda c: c.state != "cancel")
            .mapped("available_to_obligate")
        )
        if reserved > 0 and not float_is_zero(reserved, precision_digits=2):
            reasons.append(
                _("มีเงินจองงบประมาณที่ยังไม่ได้ใช้ %s บาท") % "{:,.2f}".format(reserved)
            )
        if self._has_pending_plan_transfer():
            reasons.append(_("มีใบโอนงบประมาณของแผนที่ยังดำเนินการไม่เสร็จ"))
        return reasons

    def _has_pending_plan_transfer(self):
        """Hook: a transfer into or out of the plan's dimension that has not
        posted or been cancelled yet (the budget-transfer bridge)."""
        self.ensure_one()
        return False

    def _get_plan_claims(self):
        """Hook: ``[(label, amount)]`` already claimed on the plan's money, each
        of which ``budget_amount`` must keep covering — a Floating Return can
        only take what lies above the largest. Base: what its reservations
        obligated or consumed; bridges add the totals their own documents are
        capped by (พ.1)."""
        self.ensure_one()
        used = sum(
            self.sudo()
            .budget_commitment_ids.filtered(lambda c: c.state != "cancel")
            .mapped("total_obligated")
        )
        return [(_("ผูกพัน/ตัดงบแล้ว"), used)]

    def _compute_has_held_money(self):
        held = self._held_analytic_ids(self.analytic_account_id.ids)
        for rec in self:
            rec.has_held_money = rec.analytic_account_id.id in held

    def _search_has_held_money(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))
        positive = (operator == "=") == value
        return [
            (
                "analytic_account_id",
                "in" if positive else "not in",
                self._held_analytic_ids(),
            )
        ]

    @api.model
    def _held_analytic_ids(self, analytic_ids=None):
        """Plan analytic accounts with a non-zero net posted allocation, among
        ``analytic_ids`` when given."""
        analytic_leaf = (
            ("procurement_plan_analytic_id", "in", analytic_ids)
            if analytic_ids is not None
            else ("procurement_plan_analytic_id", "!=", False)
        )
        groups = (
            self.env["budget.move.line"]
            .sudo()
            .read_group(
                [
                    ("parent_state", "=", "posted"),
                    ("move_type", "in", ["appropriation", "entry"]),
                    analytic_leaf,
                ],
                ["balance"],
                ["procurement_plan_analytic_id"],
            )
        )
        return [
            g["procurement_plan_analytic_id"][0]
            for g in groups
            if not float_is_zero(g["balance"] or 0.0, precision_digits=2)
        ]

    def _on_close(self):
        """Closing returns what the plan reserved but did not spend (คืนจอง,
        ADR-0005) so nothing stays locked; the money itself stays at the plan's
        dimension as Held Money until a Floating Return."""
        super()._on_close()
        for plan in self:
            for commitment in plan.sudo().budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            ):
                line = commitment._return_leftover(
                    source=plan, name=_("คืนเงินเหลือจ่ายเมื่อปิดแผน %s") % plan.name
                )
                if line:
                    plan.message_post(
                        body=_("คืนเงินจองที่เหลือ %s จำนวน %s บาท")
                        % (commitment.name, "{:,.2f}".format(-line.amount))
                    )
