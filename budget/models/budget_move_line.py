import logging
from contextlib import ExitStack

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

# A posted ledger line of a commitment event is the figure itself: its amount,
# budget code and coordinate may not change afterwards — undo the event instead.
_LEDGER_LOCKED_FIELDS = frozenset(
    {
        "balance",
        "debit",
        "credit",
        "account_id",
        "analytic_distribution",
        "activity_analytic_id",
        "department_analytic_id",
        "fund_analytic_id",
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
        "source_analytic_id",
        "move_type",
        "commitment_id",
        "commitment_line_id",
        "is_liquidation",
        "is_return",
        "move_id",
    }
)



class BudgetMoveLine(models.Model):
    """
    Budget Move Line - Individual line item within budget moves for detailed accounting.

    Business Purpose:
        Represents individual accounting entries within budget moves, implementing
        budget accounting with detailed analytic distribution for precise
        budget tracking and reporting.

    Key Features:
        • Budget accounting with balance tracking
        • Complete 4D analytic distribution (Activities, Departments, Funds, Sources)
        • Hierarchical analytic matching for budget availability calculations
        • Integration with budget commitments through analytic matching

    Line Types by Move Type:
        **Appropriation Lines:**
        • Regular lines: Actual budget allocation amounts
        • Positive balance: Increases budget availability

        **Consumption Lines:**
        • Track actual budget usage from commitments
        • Negative balance: Reduces budget availability
        • Links to specific budget commitments

        **Entry Lines:**
        • Manual adjustments and corrections
        • Budget transfers between accounts
        • Can be positive or negative based on operation

    Analytic Distribution:
        Each line maintains complete 4D analytic breakdown:
        • Budget Account: Specific chart of accounts item
        • Activity: งานบริหาร > งานสำนักงาน > งานธุรการ
        • Department: สำนักงานอธิการบดี > งานบุคคล
        • Fund: เงินรายได้ > เงินค่าบำรุง
        • Source: เงินแผ่นดิน, เงินนอกงบประมาณ
    """

    _name = "budget.move.line"
    _description = "Budget Move Line"
    _inherit = ["analytic.distribution.mixin", "mail.thread"]
    _order = "date desc, move_name desc, id"

    move_id = fields.Many2one(
        comodel_name="budget.move",
        string="Budget Move",
        copy=True,
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )
    move_name = fields.Char(
        string="Number",
        related="move_id.name",
        store=True,
        index="btree",
    )
    date = fields.Date(related="move_id.date", store=True)
    code = fields.Char(related="account_id.code", store=True, tracking=True)
    name = fields.Char("ชื่อรายการ", related="account_id.name", store=True, tracking=True)
    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        index=True,
        required=True,
        # TODO: ต้องกรองข้อมูลเฉพาะรหัสงบประมาณ ที่อยู่ภายใต้กองทุนที่เลือกเท่านั้น
        domain="[('budget_type', '=', budget_type)]",
        tracking=True,
    )
    budget_type = fields.Selection(
        related="move_id.budget_type", store=True, readonly=True
    )
    debit = fields.Float(
        string="เดบิต",
        digits="Budget Precision",
        help="จำนวนเงินฝั่งเดบิต (การจัดสรรงบประมาณ, การรับโอนงบประมาณ)",
        tracking=True,
        default=0.0,
    )
    credit = fields.Float(
        string="เครดิต",
        digits="Budget Precision",
        help="จำนวนเงินฝั่งเครดิต (การใช้งบประมาณ, การโอนงบประมาณออก)",
        tracking=True,
        default=0.0,
    )
    balance = fields.Float(
        string="จำนวนเงิน",
        digits="Budget Precision",
        tracking=True,
        default=0.0,
    )
    unallocated_balance = fields.Float(
        string="ยังไม่ระบุรายการ",
        help="จำนวนเงินที่ยังไม่มีการวางแผนการใช้งาน แต่ต้องการจองจำนวนเงินไว้ก่อน",
        store=True,
        required=False,
        digits="Budget",
        compute="_compute_unallocated_balance",
    )
    note = fields.Text(string="หมายเหตุ", tracking=True)
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        domain=[("root_plan_id.code", "=", "departments")],
        compute="_compute_department_analytic",
        store=True,
        readonly=False,
    )

    # === Parent fields === #
    source_analytic_id = fields.Many2one(
        related="move_id.source_analytic_id", store=True
    )
    account_fiscal_year_id = fields.Many2one(related="move_id.account_fiscal_year_id", store=True)
    parent_state = fields.Selection(related="move_id.state", store=True)
    # The bucket a line moves (ADR-0016, Q4): defaults to the move's type, but
    # a liquidation line inside an obligate/consume move — or a reservation
    # top-up inside a transfer move — names its own bucket.
    move_type = fields.Selection(
        selection="_selection_move_type",
        compute="_compute_move_type",
        store=True,
        readonly=False,
        index=True,
    )
    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="ใบจองงบประมาณ",
        index=True,
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    commitment_line_id = fields.Many2one(
        comodel_name="budget.commitment.line",
        string="เหตุการณ์ใบจอง",
        index=True,
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    is_liquidation = fields.Boolean(
        string="ปลดจอง",
        readonly=True,
        copy=False,
        help="Moves money out of the previous bucket as a reservation advances "
        "(reserve → obligate → consume).",
    )
    is_return = fields.Boolean(
        string="ส่งคืนเงินเหลือจ่าย",
        readonly=True,
        copy=False,
    )
    appropriation_type = fields.Selection(
        related="move_id.appropriation_type", store=True
    )
    company_id = fields.Many2one(related="move_id.company_id", store=True)
    currency_id = fields.Many2one(
        string="Currency", related="company_id.currency_id", store=True
    )
    company_currency_id = fields.Many2one(
        string="Company Currency", related="company_id.currency_id", store=True
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        domain=[("root_plan_id.code", "=", "funds")],
    )
    # Stored columns for the two dimensions that have no dedicated column upstream
    # (kmitl_project / procurement_plan). Folded into ``_analytic_keys`` below so
    # they round-trip with analytic_distribution exactly like the base four dims —
    # editable by the user and readable by the availability engine (set-based
    # read_group/child_of). The JSON distribution stays the source of truth.
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="โครงการ/กิจกรรม",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "kmitl_project")],
    )
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แผนจัดซื้อจัดจ้าง",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "procurement_plan")],
    )
    # Account-type flags — drive conditional visibility of the two extra dims in
    # the move-line form. Both come from optional modules (kmitl_project /
    # procurement_plan); guard against missing fields so budget installs standalone.
    account_is_project = fields.Boolean(
        string="Is Project Account",
        compute="_compute_account_type_flags",
    )
    account_is_procurement = fields.Boolean(
        string="Is Procurement Account",
        compute="_compute_account_type_flags",
    )
    hide_unallocated_balance = fields.Boolean(
        compute="_compute_hide_unallocated_balance", readonly=True
    )

    _sql_constraints = [
        (
            "debit_credit_positive",
            "CHECK (debit >= 0 AND credit >= 0)",
            "เดบิตและเครดิตต้องมีค่าไม่ติดลบ"
        ),
        (
            "debit_credit_exclusive",
            "CHECK ((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0) OR (debit = 0 AND credit = 0))",
            "ไม่สามารถมีค่าเดบิตและเครดิตพร้อมกันได้ ต้องเลือกใดเลือกหนึ่ง"
        ),
    ]

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if "default_activity_analytic_id" in self.env.context:
            res["activity_analytic_id"] = self.env.context[
                "default_activity_analytic_id"
            ]
        if "default_fund_analytic_id" in self.env.context:
            res["fund_analytic_id"] = self.env.context["default_fund_analytic_id"]
        return res

    @api.depends("move_id", "move_id.department_analytic_id", "move_id.move_type")
    def _compute_department_analytic(self):
        for line in self:
            if line.move_id and line.move_id.move_type == "appropriation":
                # ใช้ department จาก move สำหรับ appropriation
                line.department_analytic_id = line.move_id.department_analytic_id
            # สำหรับ move types อื่น ให้ผู้ใช้เลือกเอง

    def _analytic_keys(self):
        """Extend the base 4-dim mapping with the two extra dims so
        analytic_distribution round-trips all six dimensions (kmitl_project /
        procurement_plan become editable convenience fields, not read-only mirrors).
        """
        keys = super()._analytic_keys()
        keys["kmitl_project"] = "kmitl_project_analytic_id"
        keys["procurement_plan"] = "procurement_plan_analytic_id"
        return keys

    @api.depends("account_id")
    def _compute_account_type_flags(self):
        has_project = "is_project" in self.env["budget.account"]._fields
        has_proc = "procurement_plan" in self.env["budget.account"]._fields
        for line in self:
            acc = line.account_id
            line.account_is_project = bool(acc and has_project and acc.is_project)
            line.account_is_procurement = bool(
                acc and has_proc and acc.procurement_plan
            )

    def _compute_hide_unallocated_balance(self):
        for line in self:
            line.hide_unallocated_balance = True

    def _compute_unallocated_balance(self):
        for rec in self:
            rec.unallocated_balance = 0

    @api.onchange("balance")
    def _onchange_balance(self):
        """แปลงค่า balance เป็น debit/credit อัตโนมัติ"""
        for line in self:
            if line.balance > 0:
                # ค่าบวก: ใส่ในฝั่งเดบิต (การจัดสรร/รับโอน)
                line.debit = line.balance
                line.credit = 0.0
            elif line.balance < 0:
                # ค่าลบ: ใส่ในฝั่งเครดิต (การใช้/โอนออก)
                line.debit = 0.0
                line.credit = abs(line.balance)
            else:
                # ค่าศูนย์: เคลียร์ทั้งคู่
                line.debit = 0.0
                line.credit = 0.0

    @api.constrains("debit", "credit")
    def _check_debit_credit_rules(self):
        """ตรวจสอบกฎสำหรับเดบิตและเครดิต"""
        for line in self:
            # ตรวจสอบค่าไม่ติดลบ
            if line.debit < 0:
                raise ValidationError(
                    _("เดบิตต้องมีค่าไม่ติดลบ (รายการ: %s)") % line.name
                )
            if line.credit < 0:
                raise ValidationError(
                    _("เครดิตต้องมีค่าไม่ติดลบ (รายการ: %s)") % line.name
                )

            # ตรวจสอบว่าไม่สามารถมีทั้งเดบิตและเครดิตพร้อมกัน
            if line.debit > 0 and line.credit > 0:
                raise ValidationError(
                    _("ไม่สามารถมีค่าเดบิตและเครดิตพร้อมกันได้ ต้องเลือกใดเลือกหนึ่ง (รายการ: %s)") % line.name
                )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create budget move lines.
        """
        moves = self.env["budget.move"].browse({vals["move_id"] for vals in vals_list})
        container = {"records": self}
        move_container = {"records": moves}

        with ExitStack() as exit_stack:
            # Create all lines
            lines = super().create([self._sanitize_vals(vals) for vals in vals_list])

            exit_stack.enter_context(
                self.env.protecting(
                    [
                        protected
                        for vals, line in zip(vals_list, lines)
                        for protected in self.env["budget.move"]._get_protected_vals(
                            vals, line
                        )
                    ]
                )
            )
            container["records"] = lines

        lines._check_no_orphan_usage_on_posted()
        return lines

    @api.model
    def _selection_move_type(self):
        return self.env["budget.move"]._fields["move_type"]._description_selection(
            self.env
        )

    @api.depends("move_id.move_type")
    def _compute_move_type(self):
        for line in self:
            line.move_type = line.move_id.move_type

    # ------------------------------------------------------------------
    # Direct consumption (ตัดงบตรง, ADR-0018)
    # ------------------------------------------------------------------
    _DIRECT_CONSUME_REQUIRED_DIMS = (
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    )

    def _ledger_coordinate(self):
        """{analytic id: 100} of this line's dimensions, read from the stored
        columns the availability engine matches on."""
        self.ensure_one()
        columns = self.env["budget.controller"]._DIM_COLUMNS.values()
        return {str(self[col].id): 100.0 for col in columns if self[col]}

    def _check_direct_consume(self):
        """A consume without a reservation draws the pool directly, so it must
        name its full coordinate and fit the control node's Available — the
        reservation check it skips (ADR-0018). Lines are summed per control
        node, like a reservation's codes."""
        if self.filtered(lambda l: l.budget_type != "expense"):
            raise UserError(_("A direct consumption is posted on expense budget only."))
        missing = self.filtered(
            lambda l: not all(l[f] for f in self._DIRECT_CONSUME_REQUIRED_DIMS)
        )
        if missing:
            raise UserError(
                _(
                    "A direct consumption must carry ส่วนงาน, แหล่งเงิน, กองทุน "
                    "and กิจกรรม: %s"
                )
                % ", ".join(missing.mapped("account_id.display_name"))
            )
        if (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        ):
            return
        # The pool is read whole: operating-unit rules must not hide another
        # unit's draw on a shared pool from the check.
        controller = self.env["budget.controller"].sudo()
        pools = {}
        for line in self:
            fy_id = line.move_id.account_fiscal_year_id.id
            company_id = line.company_id.id or self.env.company.id
            dims = controller._parse_dimensions(line._ledger_coordinate())
            controls = controller._resolve_control_nodes(
                line.account_id, dims, fy_id, company_id
            )
            key = (
                fy_id,
                company_id,
                controls["account"].id,
                tuple(sorted((col, rec.id) for col, rec in controls["dims"].items())),
            )
            pool = pools.setdefault(
                key, [controls, dims, fy_id, company_id, 0.0, line.account_id.browse()]
            )
            pool[4] -= line.balance
            pool[5] |= line.account_id
        for controls, dims, fy_id, company_id, amount, accounts in pools.values():
            available = controller._sum_available(controls, dims, fy_id, company_id)
            rounding = self.env.company.currency_id.rounding or 0.01
            if float_compare(available, amount, precision_rounding=rounding) < 0:
                raise UserError(
                    _(
                        "Insufficient budget for a direct consumption of "
                        "%(amount).2f on %(code)s: only %(available).2f available "
                        "at the control node."
                    )
                    % {
                        "amount": amount,
                        "code": ", ".join(accounts.mapped("display_name")),
                        "available": available,
                    }
                )

    def _check_direct_consume_lines_locked(self):
        """The lines of a posted direct consumption are the figure itself, like
        a reservation's ledger lines: they are not edited or deleted in place.
        A Budget Manager resets the move instead, which re-runs every check
        when it is posted again (ADR-0018)."""
        if self.env.context.get("budget_ledger_posting"):
            return
        if self.filtered(
            lambda l: l.parent_state == "posted"
            and l.move_type == "consume"
            and not l.commitment_id
        ):
            raise UserError(
                _(
                    "Cannot change a posted direct consumption (ตัดงบตรง) line. "
                    "Reset the budget move to draft first."
                )
            )

    def _check_no_orphan_usage_on_posted(self):
        """No reserve/obligate/consume line without a reservation may appear on
        an already-posted move — by adding a line or re-typing one — which
        would skip the posting checks (ADR-0016/0018)."""
        if self.env.context.get("budget_ledger_posting"):
            return
        if self.filtered(
            lambda l: l.parent_state == "posted"
            and l.move_type in ("reserve", "obligate", "consume")
            and not l.commitment_id
        ):
            raise UserError(
                _(
                    "Reservation, obligation and consumption lines cannot be "
                    "added to a posted budget move. Reset it to draft first."
                )
            )

    def unlink(self):
        self._check_direct_consume_lines_locked()
        if not self.env.context.get("budget_ledger_posting") and self.filtered(
            lambda l: l.commitment_id and l.parent_state == "posted"
        ):
            raise UserError(
                _(
                    "Cannot delete a posted budget ledger line of a commitment. "
                    "Cancel the commitment event instead."
                )
            )
        return super().unlink()

    def write(self, vals):
        """
        Update budget move lines.
        """
        if not vals:
            return True
        if _LEDGER_LOCKED_FIELDS & set(vals):
            self._check_direct_consume_lines_locked()
        if _LEDGER_LOCKED_FIELDS & set(vals) and not self.env.context.get(
            "budget_ledger_posting"
        ):
            if self.filtered(lambda l: l.commitment_id and l.parent_state == "posted"):
                raise UserError(
                    _(
                        "Cannot edit a posted budget ledger line of a commitment. "
                        "Cancel the commitment event instead."
                    )
                )
        vals = self._sanitize_vals(vals)

        # Handle tracking
        if not self.env.context.get("tracking_disable", False):
            # Get trackable fields from vals
            tracking_fields = []
            for field_name in vals:
                field = self._fields.get(field_name)
                if field and hasattr(field, "tracking") and field.tracking:
                    tracking_fields.append(field_name)

            # Store initial values for tracking
            move_initial_values = {}
            if tracking_fields:
                ref_fields = self.fields_get(tracking_fields)
                for line in self:
                    if line.move_id.id not in move_initial_values:
                        move_initial_values[line.move_id.id] = {}
                    for field in tracking_fields:
                        move_initial_values[line.move_id.id][field] = line[field]

        # Normal write process
        result = super().write(vals)
        if {"move_type", "move_id", "commitment_id"} & set(vals):
            self._check_no_orphan_usage_on_posted()

        # Process tracking after write
        if not self.env.context.get("tracking_disable", False) and move_initial_values:
            for move_id, initial_values in move_initial_values.items():
                for line in self.filtered(
                    lambda budget_line: budget_line.move_id.id == move_id
                ):
                    tracking_value_ids = line._mail_track(ref_fields, initial_values)[1]
                    if tracking_value_ids:
                        msg = _(
                            "Budget Item %s updated",
                            line._get_html_link(title=f"#{line.id}"),
                        )
                        line.move_id._message_log(
                            body=msg, tracking_value_ids=tracking_value_ids
                        )
        return result

    def _sanitize_vals(self, vals):
        """ปรับแต่ง values ก่อน create/write เพื่อ sync balance กับ debit/credit"""
        if 'balance' in vals:
            balance = vals['balance']
            if balance > 0:
                vals.update({'debit': balance, 'credit': 0.0})
            elif balance < 0:
                vals.update({'debit': 0.0, 'credit': abs(balance)})
            else:
                vals.update({'debit': 0.0, 'credit': 0.0})

        return vals
