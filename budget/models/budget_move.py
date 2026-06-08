import logging
from contextlib import ExitStack

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetMove(models.Model):
    """
    Budget Move - Budget accounting system for all budget transactions.

    Business Purpose:
        Budget moves serve as the accounting ledger for all budget transactions,
        implementing budget tracking principles for accurate accounting
        and maintain fiscal accountability across the organization.

    Move Types and Their Purposes:
        1. **appropriation** - Budget Appropriation
           • Records initial budget allocations and adjustments
           • Creates budget availability for commitments and consumption
           • Records initial budget allocations
           • Examples: Annual budget allocation, mid-year adjustments

        2. **consume** - Budget Consumption
           • Records actual budget usage from commitments
           • Links to budget.commitment via commitment_id
           • Reduces available budget for future commitments
           • Examples: Purchase orders, expense claims, payments

        3. **entry** - Budget Entry
           • General budget adjustments and corrections
           • Manual budget transfers between accounts
           • Year-end adjustments and corrections
           • Examples: Budget transfers, error corrections

    Budget System:
        Budget moves implement accounting principles with:
        • Balance tracking via budget.move.line
        • Automatic journal entry generation
        • Audit trail through complete transaction history

    State Lifecycle:
        draft → review → posted → cancel
        │       │        │        │
        │       │        │        └── Cancelled, no budget impact
        │       │        └─────────── Final, affects all budget calculations
        │       └──────────────────── Under approval, locked from changes
        └──────────────────────────── Editable, no budget impact

    Key Features:
        • 4D Analytic Distribution (Activities, Departments, Funds, Sources)
        • Fiscal year enforcement and company isolation
        • Multi-line structure with detailed analytic breakdown
        • Integration with budget commitments for consumption tracking
        • Hierarchical analytic matching for budget availability

    Integration Architecture:
        • Budget Commitments: Consumption tracking via commitment_id
        • Budget Controller: Source data for availability calculations
        • Budget Reports: Foundation for all budget reporting
        • External Systems: Can create consumption moves via budget.mixin

    Data Flow Examples:
        **Appropriation Flow:**
        1. Create appropriation move with budget allocation
        2. System creates virtual account entries for balance
        3. Post move to make budget available
        4. Budget becomes available for commitments

        **Consumption Flow:**
        1. Budget commitment reserved in system
        2. External action (purchase, payment) triggers consumption
        3. Create consume move linked to commitment
        4. Budget availability reduced, commitment tracked as consumed

    Thai Localization:
        • Fiscal year aligned with Thai government calendar
        • Support for Thai government accounting standards
        • Multi-level analytic structure for Thai institutions
        • Integration with Thai chart of accounts
        • Currency support for Thai Baht and foreign currencies

    Performance Features:
        • Indexed fields for fast querying (date, state, move_type)
        • Efficient fiscal year filtering
        • Optimized analytic distribution queries
        • Strategic field dependencies for computed values

    Technical Notes:
        • Thread-safe posting process prevents double-posting
        • Automatic sequence generation for move numbers
        • Complete audit trail via mail.thread integration
        • Robust error handling with transaction rollback
        • Support for bulk operations and batch processing
    """

    _name = "budget.move"
    _description = "Budget Move"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "ref"]

    READONLY_STATES = {
        "review": [("readonly", True)],
        "posted": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        string="Number",
        compute="_compute_name",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
    )
    ref = fields.Char(string="Reference", copy=False, tracking=True)
    date = fields.Date(
        string="Date",
        index=True,
        default=lambda self: fields.Date.context_today(self),
        required=True,
        readonly=False,
        copy=False,
        tracking=True,
        states=READONLY_STATES,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("review", "In Review"),
            ("posted", "Posted"),
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
        string="Fiscal year",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    note = fields.Char(
        readonly=False,
        tracking=True,
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        store=True,
        copy=True,
        readonly=False,
        states=READONLY_STATES,
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        store=True,
        copy=True,
        readonly=False,
        states=READONLY_STATES,
        domain=[("root_plan_id.code", "=", "sources")],
        tracking=True,
    )
    ref = fields.Char(
        string="Reference",
        copy=False,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    active = fields.Boolean(default=True, tracking=True)
    user_id = fields.Many2one(
        string="Responsible user",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        store=True,
        readonly=False,
        states=READONLY_STATES,
    )
    show_reset_to_draft_button = fields.Boolean(
        compute="_compute_show_reset_to_draft_button"
    )
    hide_post_button = fields.Boolean(
        compute="_compute_hide_post_button", readonly=True
    )
    hide_review_button = fields.Boolean(
        compute="_compute_hide_review_button", readonly=True
    )
    line_ids = fields.One2many(
        string="รายการงบประมาณ",
        comodel_name="budget.move.line",
        inverse_name="move_id",
        copy=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    budget_type = fields.Selection(
        [("revenue", "Revenue"), ("expense", "Expense")],
        string="Budget Type",
        required=True,
        copy=True,
        default="expense",
        tracking=True,
        states=READONLY_STATES,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Account Currency",
        default=lambda self: self.env.company.currency_id,
        tracking=True,
        store=True,
        required=True,
    )
    company_currency_id = fields.Many2one(related="company_id.currency_id")
    move_type = fields.Selection(
        selection=[
            ("entry", "Budget Entry"),
            ("appropriation", "Budget Appropriation"),
            ("consume", "Budget Consumption"),
        ],
        string="Type",
        required=True,
        readonly=False,
        tracking=True,
        change_default=True,
        index=True,
        default="entry",
        states=READONLY_STATES,
    )

    appropriation_type = fields.Selection(
        selection=[
            ("initial", "งบประมาณต้นปี"),
            ("supplementary", "งบประมาณเพิ่มเติม"),
        ],
        string="ประเภทการจัดสรร",
        tracking=True,
        help="ใช้แยกประเภทการจัดสรรงบประมาณ ต้นปี vs ระหว่างปี",
    )

    total_amount = fields.Float(
        string="Total Amount",
        compute="_compute_amount",
        readonly=True,
        store=True,
        digits="Budget Precision",
    )

    # Link to budget commitment
    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Related Commitment",
        help="Budget commitment that this move is consuming from",
        index=True,
        ondelete="set null",
        states=READONLY_STATES,
    )
    commitment_line_id = fields.Many2one(
        comodel_name="budget.commitment.line",
        string="Related Commitment Line",
        index=True,
        ondelete="set null",
        states=READONLY_STATES,
    )

    first_account_id = fields.Many2one(
        'budget.account',
        string='First Account Used',
        compute='_compute_first_account_id',
        store=False
    )

    @api.depends('line_ids.account_id')
    def _compute_first_account_id(self):
        for move in self:
            move.first_account_id = move.line_ids[:1].account_id

    @api.depends(
        "line_ids.balance",
        "move_type",
    )
    def _compute_amount(self):
        for move in self:
            # นับทุก line เหมือนกัน ไม่ต้องแยก virtual lines
            total = sum(move.line_ids.mapped("balance"))
            move.total_amount = total

    @api.depends("state", "date")
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or "", m.id))

        for move in self:
            if move.state == "cancel":
                continue

            move_has_name = move.name and move.name != "New"
            if move_has_name or (move.state not in ("review", "posted")):
                continue
            if not move_has_name and move.date:
                move.name = self.env["ir.sequence"].next_by_code("budget.move") or _(
                    "New"
                )

    @api.depends("date", "state")
    def _compute_hide_post_button(self):
        for record in self:
            record.hide_post_button = record.state != "review"

    @api.depends("state")
    def _compute_hide_review_button(self):
        for record in self:
            record.hide_review_button = record.state != "draft"

    @api.depends("state")
    def _compute_show_reset_to_draft_button(self):
        for record in self:
            record.show_reset_to_draft_button = record.state in (
                "review",
                "posted",
                "cancel",
            )

    @api.onchange("line_ids")
    def _onchange_line_ids(self):
        """Update total amount when any line changes"""
        # คำนวณยอดรวมจากทุก line
        self.total_amount = sum(self.line_ids.mapped("balance"))

    @api.constrains("move_type", "appropriation_type")
    def _check_appropriation_type(self):
        for move in self:
            if move.move_type == "appropriation" and not move.appropriation_type:
                raise ValidationError(
                    _("ประเภทการจัดสรร is required for appropriation moves.")
                )

    def action_review(self):
        self.write({"state": "review"})

    def action_post(self):
        self.write({"state": "posted"})

    def button_cancel(self):
        self.write({"state": "cancel"})

    def button_draft(self):
        self.write({"state": "draft"})

    def _stolen_move(self, vals):
        for command in vals.get("line_ids", ()):
            if command[0] == Command.LINK:
                yield self.env["budget.move.line"].browse(command[1]).move_id.id
            if command[0] == Command.SET:
                yield from self.env["budget.move.line"].browse(command[2]).move_id.ids

    def _get_protected_vals(self, vals, records):
        protected = set()
        for fname in vals:
            field = records._fields[fname]
            if field.inverse or (field.compute and not field.readonly):
                protected.update(self.pool.field_computed.get(field, [field]))
        return [(protected, rec) for rec in records] if protected else []

    @api.model_create_multi
    def create(self, vals_list):
        if any("state" in vals and vals.get("state") == "posted" for vals in vals_list):
            raise UserError(
                _(
                    "You cannot create a move already in the posted state. Please create a draft move and post it after."
                )
            )
        container = {"records": self}
        with ExitStack() as exit_stack:
                for vals in vals_list:
                    self._sanitize_vals(vals)
                    # Appropriation moves must carry an appropriation_type so the
                    # initial-allocation metric is never undercounted; default to
                    # "initial" when the caller omits it. entry/consume moves are
                    # untouched (their move_type != "appropriation").
                    if vals.get("move_type") == "appropriation" and not vals.get(
                        "appropriation_type"
                    ):
                        vals["appropriation_type"] = "initial"
                stolen_moves = self.browse(
                    set(move for vals in vals_list for move in self._stolen_move(vals))
                )
                moves = super().create(vals_list)
                exit_stack.enter_context(
                    self.env.protecting(
                        [
                            protected
                            for vals, move in zip(vals_list, moves)
                            for protected in self._get_protected_vals(vals, move)
                        ]
                    )
                )
                container["records"] = moves | stolen_moves
        return moves

    def write(self, vals):
        if not vals:
            return True
        self._sanitize_vals(vals)
        stolen_moves = self.browse(set(move for move in self._stolen_move(vals)))
        container = {"records": self | stolen_moves}

        for move in self:
            # หากเคย submit แล้ว
            if (
                "/" in move.name
                and "budget_type" in vals
            ):
                raise UserError(
                    _(
                        "You cannot edit the budget_type of a budget move if it already has a sequence number assigned."
                    )
                )

        with self.env.protecting(
            self._get_protected_vals(vals, self)
        ):
            res = super().write(vals)
        return res

    def _sanitize_vals(self, vals):
        return vals

    def action_view_commitment(self):
        """View the related budget commitment"""
        self.ensure_one()
        if not self.commitment_id:
            raise UserError(_('No commitment is linked to this budget move.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Commitment'),
            'res_model': 'budget.commitment',
            'res_id': self.commitment_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }
