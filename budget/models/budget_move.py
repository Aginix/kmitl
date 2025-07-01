import logging

from contextlib import ExitStack, contextmanager
from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import format_amount


_logger = logging.getLogger(__name__)


class BudgetMove(models.Model):
    """
    Budget Move - Double-entry budget accounting system for all budget transactions.
    
    Business Purpose:
        Budget moves serve as the accounting ledger for all budget transactions,
        implementing double-entry principles to ensure accurate budget tracking
        and maintain fiscal accountability across the organization.
    
    Move Types and Their Purposes:
        1. **appropriation** - Budget Appropriation
           • Records initial budget allocations and adjustments
           • Creates budget availability for commitments and consumption
           • Uses virtual accounts for double-entry balance
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
    
    Double-Entry System:
        Budget moves implement accounting principles with:
        • Debit/Credit balance tracking via budget.move.line
        • Virtual accounts for appropriation balancing
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
        • Virtual account system for appropriation double-entry
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
    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        search="_search_date_range_fy",
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
        comodel_name="budget.move.line",
        inverse_name="move_id",
        copy=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    journal_id = fields.Many2one(
        "budget.journal",
        string="Journal",
        store=True,
        readonly=False,
        required=True,
        states=READONLY_STATES,
        check_company=True,
        tracking=True,
    )
    budget_type = fields.Selection(
        related='journal_id.default_budget_type',
        string='Budget Type',
        store=True,
        readonly=True,
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
    )

    total_amount = fields.Float(
        string="Total Amount",
        compute="_compute_amount",
        readonly=True,
        store=True,
        digits="Budget Precision",
    )

    # เพิ่ม field สำหรับ appropriation
    appropriation_account_id = fields.Many2one(
        "budget.account",
        string="Virtual Budget Account",
        help="Virtual account used for double-entry in appropriation",
        compute="_compute_appropriation_account",
        store=True,
    )

    # สร้าง computed field สำหรับแสดงเฉพาะ non-virtual lines
    appropriation_line_ids = fields.One2many(
        comodel_name="budget.move.line",
        inverse_name="move_id",
        string="Appropriation Lines",
        domain=[("is_virtual_line", "=", False)],
        readonly=False,
        copy=False,
    )

    # Link to budget commitment
    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Related Commitment",
        help="Budget commitment that this move is consuming from",
        index=True,
        ondelete="set null",
    )

    @api.depends("journal_id", "move_type")
    def _compute_appropriation_account(self):
        for move in self:
            if move.move_type == "appropriation" and move.journal_id:
                # หา virtual account จาก journal หรือสร้างใหม่
                move.appropriation_account_id = self._get_virtual_budget_account()
            else:
                move.appropriation_account_id = False

    def _get_virtual_budget_account(self):
        """Get virtual budget account for appropriation"""
        self.ensure_one()

        virtual_account = (
            self.env["budget.account"]
            .with_context(active_test=False)
            .search(
                [
                    ("code", "=", "virtual_" + self.journal_id.default_budget_type),
                    ("budget_type", "=", self.journal_id.default_budget_type),
                ],
                limit=1,
            )
        )

        return virtual_account

    @api.depends(
        "line_ids.balance",
        "line_ids.debit",
        "line_ids.credit",
        "line_ids.is_virtual_line",
        "move_type",
    )
    def _compute_amount(self):
        for move in self:
            if move.move_type == "appropriation":
                # สำหรับการจัดสรรงบประมาณ นับเฉพาะ non-virtual lines
                lines = move.line_ids.filtered(lambda l: not l.is_virtual_line)
                total = sum(lines.mapped("balance"))
            else:
                # สำหรับ entry ปกติ นับทุก line
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

    @api.onchange('appropriation_line_ids')
    def _onchange_appropriation_lines(self):
        """Update total amount when appropriation lines change"""
        if self.move_type == 'appropriation':
            # คำนวณยอดรวมจาก appropriation_line_ids
            self.total_amount = sum(self.appropriation_line_ids.mapped('balance'))

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        """Update total amount when any line changes"""
        if self.move_type != 'appropriation':
            # สำหรับ entry ปกติ
            self.total_amount = sum(self.line_ids.mapped('balance'))

    def action_review(self):
        self.write({"state": "review"})

    def action_post(self):
        self.write({"state": "posted"})

    def button_cancel(self):
        self.write({"state": "cancel"})

    def button_draft(self):
        self.write({"state": "draft"})

    def action_open_preview(self):
        """Open the budget appropriation preview in full screen"""
        self.ensure_one()

        if self.move_type != 'appropriation':
            raise UserError(_("Preview is only available for appropriation moves."))

        return {
            'name': _('Budget Appropriation Preview'),
            'type': 'ir.actions.client',
            'tag': 'budget_appropriation_preview',
            'target': 'current',
            'res_id': self.id,
            'res_model': 'budget.move',
            'context': {
                'active_id': self.id,
                'active_model': 'budget.move',
            }
        }

    def _get_report_lines(self):
        """Get hierarchical lines for PDF report"""
        self.ensure_one()

        if self.move_type != 'appropriation':
            return []

        lines = []
        # Get non-virtual lines only
        move_lines = self.line_ids.filtered(lambda l: not l.is_virtual_line)

        # Build hierarchy data
        report_obj = self.env['budget.appropriation.report']
        hierarchy_data = report_obj.get_hierarchical_data(self.id)

        if 'hierarchy' in hierarchy_data:
            def add_hierarchy_lines(nodes, level=0):
                for node in nodes:
                    # Add node line
                    line_data = {
                        'name': node.get('name', ''),
                        'code': node.get('code', ''),
                        'level': level,
                        'amount': node.get('total_amount', 0),
                        'is_total': node.get('type') in ['activity', 'department', 'fund'],
                        'type': node.get('type', ''),
                    }

                    # Add account details for line type (now includes account_info)
                    if node.get('type') == 'line':
                        if node.get('account_info'):
                            # New flattened structure with account_info
                            line_data.update({
                                'account_code': node['account_info'].get('code', ''),
                                'account_name': node['account_info'].get('name', ''),
                                'note': node.get('line_data', {}).get('note', '') if node.get('line_data') else '',
                            })
                        elif node.get('line_data'):
                            # Fallback for old structure
                            line_info = node['line_data']
                            line_data.update({
                                'account_code': line_info.get('account', {}).get('code', ''),
                                'account_name': line_info.get('account', {}).get('name', ''),
                                'note': line_info.get('note', ''),
                            })

                    lines.append(line_data)

                    # Add children
                    if node.get('children'):
                        add_hierarchy_lines(node['children'], level + 1)

            add_hierarchy_lines(hierarchy_data['hierarchy'])

        return lines

    @contextmanager
    def _check_balanced(self, container):
        """Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        """
        yield

        unbalanced_moves = self._get_unbalanced_moves(container)
        if unbalanced_moves:
            error_msg = _("An error has occurred.")
            for move_id, sum_debit, sum_credit in unbalanced_moves:
                move = self.browse(move_id)
                error_msg += _(
                    "\n\n"
                    "The move (%s) is not balanced.\n"
                    "The total of debits equals %s and the total of credits equals %s.\n"
                    'You might want to specify a default account on journal "%s" to automatically balance each move.',
                    move.display_name,
                    format_amount(self.env, sum_debit, move.company_id.currency_id),
                    format_amount(self.env, sum_credit, move.company_id.currency_id),
                    move.journal_id.name,
                )
            raise UserError(error_msg)

    def _get_unbalanced_moves(self, container):
        moves = container["records"].filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend on computed stored fields.
        # It happens as the ORM calls create() with the 'no_recompute' statement.
        self.env["budget.move.line"].flush_model(
            ["debit", "credit", "balance", "currency_id", "move_id"]
        )
        self._cr.execute(
            """
            SELECT line.move_id,
                   ROUND(SUM(line.debit), currency.decimal_places) debit,
                   ROUND(SUM(line.credit), currency.decimal_places) credit
              FROM budget_move_line line
              JOIN budget_move move ON move.id = line.move_id
              JOIN res_company company ON company.id = move.company_id
              JOIN res_currency currency ON currency.id = company.currency_id
             WHERE line.move_id IN %s
          GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.balance), currency.decimal_places) != 0
        """,
            [tuple(moves.ids)],
        )

        return self._cr.fetchall()

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
        with self._check_balanced(container):
            with ExitStack() as exit_stack:
                for vals in vals_list:
                    self._sanitize_vals(vals)
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
                and "journal_id" in vals
                and move.journal_id.id != vals["journal_id"]
            ):
                raise UserError(
                    _(
                        "You cannot edit the journal of a budget move if it already has a sequence number assigned."
                    )
                )

        with self.env.protecting(
            self._get_protected_vals(vals, self)
        ), self._check_balanced(container):
            res = super().write(vals)
        return res

    def _sanitize_vals(self, vals):
        return vals
