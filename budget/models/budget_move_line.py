import logging
from contextlib import ExitStack

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class BudgetMoveLine(models.Model):
    """
    Budget Move Line - Individual line item within budget moves for detailed accounting.

    Business Purpose:
        Represents individual accounting entries within budget moves, implementing
        double-entry bookkeeping with detailed analytic distribution for precise
        budget tracking and reporting.

    Key Features:
        • Double-entry accounting with debit/credit balance tracking
        • Complete 4D analytic distribution (Activities, Departments, Funds, Sources)
        • Virtual line support for appropriation balancing entries
        • Hierarchical analytic matching for budget availability calculations
        • Integration with budget commitments through analytic matching

    Line Types by Move Type:
        **Appropriation Lines:**
        • Regular lines: Actual budget allocation amounts
        • Virtual lines: Balancing entries for double-entry system
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
    code = fields.Char(
        "รหัสงบประมาณ", related="account_id.code", store=True, tracking=True
    )
    name = fields.Char("ชื่อรายการ", related="account_id.name", store=True, tracking=True)
    account_id = fields.Many2one(
        comodel_name="budget.account",
        index=True,
        required=True,
        # TODO: ต้องกรองข้อมูลเฉพาะรหัสงบประมาณ ที่อยู่ภายใต้กองทุนที่เลือกเท่านั้น
        domain="[('budget_type', '=', budget_type)]",
        tracking=True,
    )
    budget_type = fields.Selection(
        related="move_id.journal_id.default_budget_type", store=True, readonly=True
    )
    balance = fields.Float(
        digits="Budget Precision",
        help="Amount",
        readonly=False,
        tracking=True,
    )
    unallocated_balance = fields.Float(
        string="ยังไม่ระบุรายการ",
        help="จำนวนเงินที่ยังไม่มีการวางแผนการใช้งาน แต่ต้องการจองจำนวนเงินไว้ก่อน",
        store=True,
        required=False,
        digits="Budget",
    )
    credit = fields.Float(
        readonly=False,
        digits="Budget Precision",
        store=True,
        compute="_compute_balance_credit_debit",
    )
    debit = fields.Float(
        readonly=False,
        digits="Budget Precision",
        store=True,
        compute="_compute_balance_credit_debit",
    )
    note = fields.Text(tracking=True)
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
    date_range_fy_id = fields.Many2one(related="move_id.date_range_fy_id", store=True)
    parent_state = fields.Selection(related="move_id.state", store=True)
    journal_id = fields.Many2one(
        related="move_id.journal_id",
        store=True,
        precompute=True,
        index=True,
        copy=False,
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
    is_virtual_line = fields.Boolean(
        string="Is Virtual Line",
        default=False,
        help="Line created automatically for double-entry",
    )
    hide_unallocated_balance = fields.Boolean(
        compute="_compute_hide_unallocated_balance", readonly=True
    )
    source_line_id = fields.Many2one(
        comodel_name="budget.move.line",
        string="Source Line",
        help="For virtual lines, references the original appropriation line that created this virtual line",
        ondelete="cascade",
        index=True,
    )

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

    @api.depends("balance")
    def _compute_balance_credit_debit(self):
        """
        Technical Note: Balance to Debit/Credit Conversion

        Budget moves use a single 'balance' field that gets split into:
        - Positive balance → Debit column (increases budget)
        - Negative balance → Credit column (decreases budget)

        For appropriations:
        - Regular lines: Positive balance (debit) = budget allocation
        - Virtual lines: Negative balance (credit) = balancing entry
        """
        for line in self:
            if line.balance >= 0:
                line.debit = line.balance
                line.credit = 0
            else:
                line.credit = -line.balance
                line.debit = 0

    def _compute_hide_unallocated_balance(self):
        return True

    @api.onchange("balance")
    def _inverse_balance(self):
        for line in self:
            if line.balance >= 0:
                line.debit = line.balance
                line.credit = 0
            else:
                line.credit = -line.balance
                line.debit = 0

    @api.model_create_multi
    def create(self, vals_list):
        """
        Technical Note: Virtual Line Creation for Budget Appropriations

        For appropriation moves, this method automatically creates balancing entries (virtual lines)
        to maintain double-entry bookkeeping. The process:

        1. Create regular appropriation lines first
        2. For each regular line, create corresponding virtual line with source_line_id
        3. Virtual line has same analytic distribution but opposite balance
        4. Virtual line uses the appropriation virtual account

        This ensures: Total Debits = Total Credits with proper 1-1 line relationships
        """
        moves = self.env["budget.move"].browse({vals["move_id"] for vals in vals_list})
        container = {"records": self}
        move_container = {"records": moves}

        # Prepare all lines (regular + virtual) before creation
        all_vals = []
        regular_to_virtual = {}  # Track which regular line index maps to virtual line

        for vals in vals_list:
            if not vals.get("is_virtual_line"):
                all_vals.append(vals)
                move = self.env["budget.move"].browse(vals["move_id"])
                if move.move_type == "appropriation":
                    # Prepare virtual line vals now (source_line_id will be set after creation)
                    virtual_vals = self._prepare_virtual_line_vals(vals, move)
                    all_vals.append(virtual_vals)
                    # Store the mapping (regular line index -> virtual line index)
                    regular_to_virtual[len(all_vals) - 2] = len(all_vals) - 1
            else:
                all_vals.append(vals)

        with moves._check_balanced(move_container), ExitStack() as exit_stack:
            # Create all lines at once
            lines = super().create([self._sanitize_vals(vals) for vals in all_vals])

            # Set source_line_id for virtual lines after creation
            for regular_idx, virtual_idx in regular_to_virtual.items():
                if regular_idx < len(lines) and virtual_idx < len(lines):
                    regular_line = lines[regular_idx]
                    virtual_line = lines[virtual_idx]
                    # Set the source_line_id relationship
                    virtual_line.with_context(skip_virtual_update=True).write(
                        {"source_line_id": regular_line.id}
                    )

            exit_stack.enter_context(
                self.env.protecting(
                    [
                        protected
                        for vals, line in zip(all_vals, lines)
                        for protected in self.env["budget.move"]._get_protected_vals(
                            vals, line
                        )
                    ]
                )
            )
            container["records"] = lines

        return lines

    def _prepare_virtual_line_vals(self, original_vals, move, source_line_id=None):
        """
        Prepare values for virtual line (opposite entry)

        Creates the balancing entry for appropriation lines to maintain double-entry bookkeeping:
        - Flips balance sign (positive → negative, negative → positive)
        - Swaps credit/debit if explicitly provided in original values
        - Uses virtual appropriation account
        - Sets source_line_id for 1-1 relationship tracking
        - Copies analytic distribution from original line

        Args:
            original_vals (dict): Values from the regular appropriation line
            move (budget.move): The budget move record
            source_line_id (int, optional): ID of the regular line this virtual line balances

        Returns:
            dict: Values for creating the virtual line
        """
        virtual_vals = original_vals.copy()

        # สลับเครื่องหมายของ balance
        virtual_vals["balance"] = -original_vals.get("balance", 0.0)

        # สลับ credit/debit ถ้ามีการกำหนดไว้ใน original_vals
        if "credit" in original_vals or "debit" in original_vals:
            original_credit = original_vals.get("credit", 0.0)
            original_debit = original_vals.get("debit", 0.0)
            # Flip credit and debit
            virtual_vals["credit"] = original_debit
            virtual_vals["debit"] = original_credit

        # ใช้ virtual account
        virtual_vals["account_id"] = move.appropriation_account_id.id

        # Mark as virtual line
        virtual_vals["is_virtual_line"] = True

        # Set source_line_id for 1-1 relationship
        if source_line_id:
            virtual_vals["source_line_id"] = source_line_id

        # Copy analytic distribution
        if "analytic_distribution" in original_vals:
            analytic_dist = original_vals["analytic_distribution"]
            if isinstance(analytic_dist, dict):
                virtual_vals["analytic_distribution"] = analytic_dist.copy()
            else:
                virtual_vals["analytic_distribution"] = analytic_dist

        return virtual_vals

    def write(self, vals):
        """
        Technical Note: Handling Virtual Lines on Update (source_line_id tracking)

        When appropriation lines are modified (balance or analytic distribution),
        we update only the linked virtual lines using source_line_id field.
        The process:

        1. Find virtual lines linked to modified regular lines via source_line_id
        2. Update existing virtual lines or create new ones if missing
        3. Each virtual line maintains opposite balance and same analytics

        This ensures efficient targeted updates with maintained line relationships.
        """
        if not vals:
            return True
        # Store reference (for potential future use)
        vals = self._sanitize_vals(vals)

        # Technical Note: Virtual Line Update Logic
        # skip_virtual_update context prevents recursive updates when
        # we're creating/updating virtual lines themselves
        if not self.env.context.get("skip_virtual_update"):
            balance_update = "balance" in vals
            analytic_update = "analytic_distribution" in vals

            appropriation_lines = self.filtered(
                lambda line: line.move_id.move_type == "appropriation"
                and not line.is_virtual_line
            )

            if (balance_update or analytic_update) and appropriation_lines:
                # Group lines by move to handle virtual line updates per move
                moves_to_update = appropriation_lines.mapped("move_id")

                # Store tracking info before write
                tracking_info = {}
                if not self.env.context.get("tracking_disable", False):
                    tracking_fields = []
                    for field_name in vals:
                        field = self._fields.get(field_name)
                        if field and hasattr(field, "tracking") and field.tracking:
                            tracking_fields.append(field_name)

                    if tracking_fields:
                        ref_fields = self.fields_get(tracking_fields)
                        for line in appropriation_lines:
                            tracking_info[line.id] = {
                                "ref_fields": ref_fields,
                                "initial_values": {
                                    field: line[field] for field in tracking_fields
                                },
                            }

                # Apply the write
                result = super().write(vals)

                # Technical Note: Virtual Line Update Process
                # For each updated appropriation line, find and update its corresponding virtual line
                # using source_line_id to maintain 1-1 relationships
                for line in appropriation_lines:
                    # Find the virtual line linked to this regular line
                    virtual_line = self.search(
                        [
                            ("source_line_id", "=", line.id),
                            ("is_virtual_line", "=", True),
                        ],
                        limit=1,
                    )

                    if virtual_line:
                        # Update existing virtual line
                        virtual_update_vals = {}
                        if balance_update:
                            virtual_update_vals["balance"] = -line.balance
                        if analytic_update:
                            virtual_update_vals["analytic_distribution"] = (
                                line.analytic_distribution
                            )

                        if virtual_update_vals:
                            virtual_line.with_context(skip_virtual_update=True).write(
                                virtual_update_vals
                            )
                    else:
                        # Create missing virtual line (shouldn't happen in normal flow)
                        virtual_vals = self._prepare_virtual_line_vals(
                            {
                                "balance": line.balance,
                                "analytic_distribution": line.analytic_distribution,
                                "move_id": line.move_id.id,
                            },
                            line.move_id,
                            line.id,
                        )
                        self.with_context(skip_virtual_update=True).create(virtual_vals)

                # Handle tracking
                if tracking_info and not self.env.context.get(
                    "tracking_disable", False
                ):
                    for line in appropriation_lines:
                        if line.id in tracking_info:
                            tracking_value_ids = line._mail_track(
                                tracking_info[line.id]["ref_fields"],
                                tracking_info[line.id]["initial_values"],
                            )[1]
                            if tracking_value_ids:
                                msg = _(
                                    "Budget Item %s updated",
                                    line._get_html_link(title=f"#{line.id}"),
                                )
                                line.move_id._message_log(
                                    body=msg, tracking_value_ids=tracking_value_ids
                                )

                return result

        # Normal write process

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

        # Skip updating virtual lines if already handled
        if self.env.context.get("skip_virtual_update"):
            result = super().write(vals)
        else:
            result = super().write(vals)

        if not self.env.context.get("tracking_disable", False):
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
        return vals

    def unlink(self):
        """
        Technical Note: Virtual Line Management on Deletion

        When deleting appropriation lines, use source_line_id to find and delete
        corresponding virtual lines. This method:

        1. For regular lines: Find and delete linked virtual lines via source_line_id
        2. For virtual lines: Allow normal deletion (they cascade from regular lines)
        3. Maintains proper 1-1 relationships without unnecessary recreation

        This prevents "move is not balanced" errors while preserving line relationships.
        """
        # Technical Note: Cascade Deletion via source_line_id
        # Find virtual lines that should be deleted along with regular lines
        virtual_lines_to_delete = self.env["budget.move.line"]

        for line in self:
            if line.move_id.move_type == "appropriation" and not line.is_virtual_line:
                # Find virtual line linked to this regular line
                virtual_line = self.search(
                    [("source_line_id", "=", line.id), ("is_virtual_line", "=", True)],
                    limit=1,
                )
                if virtual_line:
                    virtual_lines_to_delete |= virtual_line

        # Delete regular lines first
        result = super().unlink()

        # Delete corresponding virtual lines
        if virtual_lines_to_delete.exists():
            virtual_lines_to_delete.with_context(skip_virtual_update=True).unlink()

        return result

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if "hide_virtual_lines" in self.env.context:
            domain = domain or []
            domain.append(("is_virtual_line", "=", False))
        return super().search_read(domain, fields, offset, limit, order)
