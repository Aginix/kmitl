import logging
from odoo import Command, api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

# Fields that should be extracted from header vals into a commitment line
_LINE_FIELDS = [
    "account_id",
    "amount",
    "activity_analytic_id",
    "fund_analytic_id",
    "analytic_distribution",
]


class BudgetCommitment(models.Model):
    """
    Budget Commitment - Reserve budget amounts before consumption.

    Implements a ledger-based architecture where each commitment can have
    lines of type 'reserve', 'obligate', or 'consume', each targeting a
    specific budget account and analytic combination.

    State Lifecycle:
        draft → in_progress → done
        cancel ← (draft or in_progress)
    """

    _name = "budget.commitment"
    _description = "Budget Commitment"
    _inherit = ["analytic.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "ref"]

    READONLY_STATES = {
        "in_progress": [("readonly", True)],
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
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
        compute="_compute_state",
        store=True,
    )

    # === Control Flags (drive computed state) === #

    is_approved = fields.Boolean(
        default=False,
        copy=False,
        help="Set when commitment is started via action_start()",
    )

    is_cancelled = fields.Boolean(
        default=False,
        copy=False,
        help="Set when commitment is cancelled via action_cancel()",
    )

    is_closed = fields.Boolean(
        default=False,
        copy=False,
        help="Set when commitment is closed/done via action_done()",
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

    notes = fields.Text(
        string="Notes",
    )

    # === Commitment Lines === #

    line_ids = fields.One2many(
        comodel_name="budget.commitment.line",
        inverse_name="commitment_id",
        string="Commitment Lines",
        copy=True,
    )

    # === Computed Header Fields (from lines, backward compat) === #

    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        compute="_compute_header_from_lines",
        inverse="_inverse_account_id",
        store=True,
        index=True,
        tracking=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
        states=READONLY_STATES,
    )

    amount = fields.Monetary(
        string="จำนวนเงินจอง",
        compute="_compute_header_from_lines",
        inverse="_inverse_amount",
        store=True,
        currency_field="currency_id",
        tracking=True,
        states=READONLY_STATES,
    )

    # Override analytic_distribution from analytic.mixin to compute from lines
    analytic_distribution = fields.Json(
        "Analytic",
        compute="_compute_header_from_lines",
        inverse="_inverse_analytic_distribution",
        store=True,
        copy=True,
        readonly=False,
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

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        domain=[("root_plan_id.code", "=", "departments")],
        store=True,
        tracking=True,
        readonly=False,
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

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
        store=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "funds": "fund_analytic_id",
    }

    @api.depends("analytic_distribution")
    def _compute_analytic_id(self):
        """Override to only compute activity and fund from analytic_distribution.

        Department and source are stored directly on the header.
        """
        for rec in self:
            rec.activity_analytic_id = False
            rec.fund_analytic_id = False
            for aid_str in rec.analytic_distribution or {}:
                if str(aid_str).isdigit():
                    account = self.env["account.analytic.account"].browse(
                        int(aid_str)
                    )
                    if account.exists():
                        field_name = self._analytic_keys.get(
                            account.plan_id.code
                        )
                        if field_name:
                            rec[field_name] = account.id

    def _inverse_activity_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("activities")

    def _inverse_fund_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("funds")

    # Budget account related fields
    budget_account_code = fields.Char(
        related="account_id.code",
        store=True,
        string="Budget Code",
    )

    budget_account_name = fields.Char(
        related="account_id.name",
        store=True,
        string="Budget Account Name",
    )

    budget_type = fields.Selection(
        related="account_id.budget_type",
        store=True,
        string="Budget Type",
    )

    # === Ledger Balance Fields === #

    total_reserve = fields.Monetary(
        string="Total Reserved",
        compute="_compute_ledger_balances",
        store=True,
        currency_field="currency_id",
    )

    total_obligated = fields.Monetary(
        string="Total Obligated",
        compute="_compute_ledger_balances",
        store=True,
        currency_field="currency_id",
    )

    reserved_balance = fields.Monetary(
        string="Reserved Balance",
        compute="_compute_ledger_balances",
        store=True,
        currency_field="currency_id",
        help="Reserve - Obligate - Consumed (free reserve)",
    )

    obligated_balance = fields.Monetary(
        string="Obligated Balance",
        compute="_compute_ledger_balances",
        store=True,
        currency_field="currency_id",
        help="Net obligation - Consumed (outstanding obligation)",
    )

    # === Consumption Tracking === #

    consumed_amount = fields.Monetary(
        string="Consumed Amount",
        compute="_compute_consumed_amount",
        store=True,
        currency_field="currency_id",
    )

    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_remaining_amount",
        store=True,
        currency_field="currency_id",
    )

    # === Budget Availability === #

    available_budget_amount = fields.Monetary(
        string="Available Budget",
        compute="_compute_available_budget",
        store=True,
        currency_field="currency_id",
    )

    budget_availability_status = fields.Selection(
        selection=[
            ("sufficient", "Sufficient"),
            ("warning", "Warning"),
            ("insufficient", "Insufficient"),
        ],
        string="Budget Status",
        compute="_compute_available_budget",
        store=True,
    )

    budget_availability_percentage = fields.Float(
        string="% of Available",
        compute="_compute_available_budget",
        store=True,
    )

    # Related budget moves for consumption tracking
    budget_move_ids = fields.One2many(
        comodel_name="budget.move",
        inverse_name="commitment_id",
        string="Related Budget Moves",
        readonly=True,
    )

    # === Compute: State === #

    @api.depends(
        "is_approved",
        "is_cancelled",
        "is_closed",
    )
    def _compute_state(self):
        """Compute header state from control flags."""
        for rec in self:
            if rec.is_cancelled:
                rec.state = "cancel"
            elif rec.is_closed:
                rec.state = "done"
            elif rec.is_approved:
                rec.state = "in_progress"
            else:
                rec.state = "draft"

    # === Compute: Ledger Balances === #

    @api.depends(
        "line_ids.line_type",
        "line_ids.amount",
    )
    def _compute_ledger_balances(self):
        """Compute reserve/obligate/consume balances from ledger lines."""
        for rec in self:
            reserve = sum(
                l.amount for l in rec.line_ids if l.line_type == "reserve"
            )
            obligate = sum(
                l.amount for l in rec.line_ids if l.line_type == "obligate"
            )
            consumed = sum(
                abs(l.amount) for l in rec.line_ids if l.line_type == "consume"
            )
            rec.total_reserve = reserve
            rec.total_obligated = obligate
            rec.reserved_balance = reserve - obligate - consumed
            rec.obligated_balance = max(0.0, obligate - consumed)

    # === Compute: Header from Lines === #

    @api.depends(
        "line_ids.account_id",
        "line_ids.amount",
        "line_ids.analytic_distribution",
        "line_ids.line_type",
    )
    def _compute_header_from_lines(self):
        """Compute header fields from reserve lines for backward compat."""
        for rec in self:
            reserve_lines = rec.line_ids.filtered(
                lambda l: l.line_type == "reserve"
            )
            first_line = reserve_lines[:1]
            rec.account_id = first_line.account_id
            rec.amount = sum(l.amount for l in reserve_lines)
            rec.analytic_distribution = first_line.analytic_distribution or False

    def _inverse_account_id(self):
        """When header account_id is set, apply to first reserve line."""
        for rec in self:
            reserve_lines = rec.line_ids.filtered(
                lambda l: l.line_type == "reserve"
            )
            if len(reserve_lines) == 1:
                reserve_lines.account_id = rec.account_id

    def _inverse_amount(self):
        """When header amount is set, apply to first reserve line."""
        for rec in self:
            reserve_lines = rec.line_ids.filtered(
                lambda l: l.line_type == "reserve"
            )
            if len(reserve_lines) == 1:
                reserve_lines.amount = rec.amount

    def _inverse_analytic_distribution(self):
        """When header analytic_distribution is set, apply to first reserve line."""
        for rec in self:
            reserve_lines = rec.line_ids.filtered(
                lambda l: l.line_type == "reserve"
            )
            if len(reserve_lines) == 1:
                reserve_lines.analytic_distribution = rec.analytic_distribution

    # === Compute: Consumed / Remaining === #

    @api.depends(
        "line_ids.line_type",
        "line_ids.amount",
    )
    def _compute_consumed_amount(self):
        """Calculate consumed amount from consume lines."""
        for record in self:
            record.consumed_amount = sum(
                abs(l.amount)
                for l in record.line_ids
                if l.line_type == "consume"
            )

    @api.depends("amount", "consumed_amount")
    def _compute_remaining_amount(self):
        for record in self:
            record.remaining_amount = record.amount - record.consumed_amount

    # === Compute: Budget Availability === #

    @api.depends(
        "line_ids.account_id",
        "line_ids.analytic_distribution",
        "line_ids.amount",
        "line_ids.line_type",
        "account_fiscal_year_id",
        "state",
    )
    def _compute_available_budget(self):
        """Compute budget availability from reserve lines."""
        budget_controller = self.env["budget.controller"]

        for record in self:
            reserve_lines = record.line_ids.filtered(
                lambda l: l.line_type == "reserve" and l.amount > 0
            )
            if not reserve_lines:
                record.available_budget_amount = 0.0
                record.budget_availability_status = "insufficient"
                record.budget_availability_percentage = 0.0
                continue

            # Check availability for each unique analytic combination
            total_available = 0.0
            total_requested = 0.0
            all_sufficient = True

            for line in reserve_lines:
                if not all([
                    line.account_id,
                    line.activity_analytic_id,
                    line.fund_analytic_id,
                    record.account_fiscal_year_id,
                ]):
                    continue

                analytic_data = {
                    "account_id": line.account_id.id,
                    "activity_analytic_id": line.activity_analytic_id.id,
                    "department_analytic_id": (
                        line.department_analytic_id.id
                        if line.department_analytic_id
                        else False
                    ),
                    "fund_analytic_id": line.fund_analytic_id.id,
                    "source_analytic_id": (
                        line.source_analytic_id.id
                        if line.source_analytic_id
                        else False
                    ),
                }

                try:
                    available = budget_controller.get_available_budget(
                        analytic_data,
                        record.account_fiscal_year_id.id,
                        record.company_id.id,
                    )
                    # If already approved, add back own remaining amount
                    if record.is_approved and record.remaining_amount:
                        available += record.remaining_amount

                    total_available += available
                    total_requested += line.amount
                    if available < line.amount:
                        all_sufficient = False
                except Exception as e:
                    _logger.warning(
                        "Error calculating budget for commitment %s: %s",
                        record.id,
                        str(e),
                    )
                    all_sufficient = False

            record.available_budget_amount = total_available

            if total_requested <= 0:
                record.budget_availability_status = "sufficient"
                record.budget_availability_percentage = 0.0
            elif all_sufficient:
                record.budget_availability_status = "sufficient"
                record.budget_availability_percentage = (
                    (total_requested / total_available * 100)
                    if total_available > 0
                    else 0.0
                )
            else:
                allow_negative = (
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param("budget.allow_negative", False)
                )
                if allow_negative:
                    record.budget_availability_status = "warning"
                else:
                    record.budget_availability_status = "insufficient"
                record.budget_availability_percentage = (
                    (total_requested / total_available * 100)
                    if total_available > 0
                    else 999.99
                )

    # === OnChange Validations === #

    @api.onchange("fund_analytic_id", "account_id")
    def _onchange_fund_account_validation(self):
        if self.fund_analytic_id and self.account_id:
            if self.account_id.fund_analytic_ids:
                if self.fund_analytic_id not in self.account_id.fund_analytic_ids:
                    return {
                        "warning": {
                            "title": _("Fund Restriction"),
                            "message": _("Budget account %s is not allowed for fund %s")
                            % (self.account_id.name, self.fund_analytic_id.name),
                        }
                    }

    # === Create Override (old API compat) === #

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create a commitment line from old-style header vals."""
        line_analytic_fields = [
            "activity_analytic_id",
            "fund_analytic_id",
        ]
        for vals in vals_list:
            if "line_ids" not in vals and vals.get("account_id"):
                line_vals = {"line_type": "reserve"}
                for field in _LINE_FIELDS:
                    if field in vals:
                        line_vals[field] = vals.pop(field)

                # Build analytic_distribution from activity/fund IDs if not present
                if "analytic_distribution" not in line_vals:
                    distribution = {}
                    for field in line_analytic_fields:
                        aid = line_vals.pop(field, False)
                        if aid:
                            distribution[str(aid)] = 100.0
                    line_vals["analytic_distribution"] = distribution or False
                else:
                    for field in line_analytic_fields:
                        line_vals.pop(field, None)

                vals["line_ids"] = [Command.create(line_vals)]
        return super().create(vals_list)

    # === Workflow Methods === #

    def action_check_budget_availability(self):
        """Check budget availability for reserve lines."""
        self.ensure_one()

        reserve_lines = self.line_ids.filtered(
            lambda l: l.line_type == "reserve" and l.amount > 0
        )
        if not reserve_lines:
            raise UserError(_("Commitment must have at least one reserve line."))

        # Trigger recomputation
        self._compute_available_budget()

        if self.budget_availability_status == "insufficient":
            raise UserError(
                _("Insufficient budget. Available: %s, Requested: %s")
                % (
                    "{:,.2f}".format(self.available_budget_amount),
                    "{:,.2f}".format(self.amount),
                )
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Budget Check Complete"),
                "message": _("Budget availability: Sufficient - Available: %s")
                % "{:,.2f}".format(self.available_budget_amount),
                "type": "success",
                "sticky": False,
            },
        }

    def action_start(self):
        """Confirm and start: check budget, assign sequence, set is_approved."""
        for record in self:
            if record.is_approved:
                raise UserError(_("Commitment is already in progress."))

            reserve_lines = record.line_ids.filtered(
                lambda l: l.line_type == "reserve" and l.amount > 0
            )
            if not reserve_lines:
                raise UserError(_("No reserve lines to approve."))

            record.action_check_budget_availability()

            if record.name == _("New"):
                record.name = self.env["ir.sequence"].next_by_code(
                    "budget.commitment"
                ) or _("New")

            record.is_approved = True

    def action_reserve(self):
        """Backward compat alias for action_start()."""
        return self.action_start()

    def action_done(self):
        """Close the commitment."""
        for record in self:
            record.close_commitment()

    def action_cancel(self):
        """Cancel the commitment."""
        for record in self:
            if record.is_closed:
                raise UserError(
                    _("Cannot cancel commitment %s - it is already done")
                    % record.name
                )
            if record.is_cancelled:
                continue
            posted_consumes = record.line_ids.filtered(
                lambda l: l.line_type == "consume" and l.is_posted
            )
            if posted_consumes:
                raise UserError(
                    _("Cannot cancel commitment %s - it has posted "
                      "consume lines. Reverse them first.")
                    % record.name
                )
            record.is_cancelled = True
            _logger.info("Cancelled budget commitment %s", record.name)

    def action_reset_to_draft(self):
        """Reset cancelled commitment to draft."""
        for record in self:
            if not record.is_cancelled:
                raise UserError(
                    _("Only cancelled commitments can be reset to draft.")
                )
            record.is_cancelled = False
            record.is_approved = False
            record.is_closed = False
            record.line_ids.unlink()

    def action_view_budget_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Related Budget Moves"),
            "res_model": "budget.move",
            "view_mode": "tree,form",
            "domain": [("commitment_id", "=", self.id)],
            "context": {"default_commitment_id": self.id},
        }

    # === Wizard Actions === #

    def action_open_obligate_wizard(self):
        """Open wizard to add obligation lines."""
        self.ensure_one()
        return {
            "name": _("ผูกพัน (Obligate)"),
            "type": "ir.actions.act_window",
            "res_model": "budget.commitment.amount.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_commitment_id": self.id,
                "default_wizard_type": "obligate",
            },
        }

    def action_open_consume_wizard(self):
        """Open wizard to consume budget."""
        self.ensure_one()
        return {
            "name": _("ตัดงบ (Consume)"),
            "type": "ir.actions.act_window",
            "res_model": "budget.commitment.amount.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_commitment_id": self.id,
                "default_wizard_type": "consume",
            },
        }

    # === Obligate Line Helpers === #

    def add_obligate_lines(self, lines_data):
        """Create obligate line(s) on this commitment.

        Args:
            lines_data (list of dict): Each dict should contain:
                - account_id (int): Budget account ID
                - amount (float): Obligation amount (positive)
                - analytic_distribution (dict): 4D analytics JSON
                - description (str, optional): Description
        """
        self.ensure_one()
        if not self.is_approved:
            raise UserError(_("Commitment must be in progress before adding obligations."))
        if self.is_cancelled or self.is_closed:
            raise UserError(_("Cannot add obligations to a cancelled or closed commitment."))

        for data in lines_data:
            vals = {
                "commitment_id": self.id,
                "line_type": "obligate",
                "account_id": data["account_id"],
                "amount": data["amount"],
                "analytic_distribution": data.get("analytic_distribution", False),
                "description": data.get("description", ""),
            }
            self.env["budget.commitment.line"].create(vals)

    def release_obligation(self, lines_data):
        """Create negative obligate line(s) to release obligations.

        Args:
            lines_data (list of dict): Same format as add_obligate_lines,
                but amount should be positive (will be negated).
        """
        self.ensure_one()
        if self.is_cancelled or self.is_closed:
            raise UserError(
                _("Cannot release obligations on a cancelled or closed commitment.")
            )

        for data in lines_data:
            vals = {
                "commitment_id": self.id,
                "line_type": "obligate",
                "account_id": data["account_id"],
                "amount": -abs(data["amount"]),
                "analytic_distribution": data.get("analytic_distribution", False),
                "description": data.get("description", _("Release obligation")),
            }
            self.env["budget.commitment.line"].create(vals)

    # === Consume (proportional distribution across reserve lines) === #

    def consume(self, amount):
        """Create consume line(s) proportionally across reserve lines.

        Returns commitment.line recordset (does NOT auto-post).
        Use line.post_line() to post individual consume lines to budget.move.
        """
        self.ensure_one()

        if self.state != "in_progress":
            raise UserError(
                _("Can only consume from in-progress commitments")
            )

        if amount > self.remaining_amount:
            raise ValidationError(
                _("Cannot consume %.2f - only %.2f remaining in commitment")
                % (amount, self.remaining_amount)
            )

        consume_lines = self._create_consume_lines(amount)

        _logger.info(
            "Created consume lines for %.2f on commitment %s",
            amount,
            self.name,
        )

        return consume_lines

    def _create_consume_lines(self, amount):
        """Create consume line(s) proportionally across reserve lines."""
        reserve_lines = self.line_ids.filtered(
            lambda l: l.line_type == "reserve" and l.amount > 0
        )
        if not reserve_lines:
            raise UserError(_("No reserve lines to consume from."))

        total_reserve = sum(reserve_lines.mapped("amount"))
        lines = self.env["budget.commitment.line"]
        distributed = 0.0

        for i, rline in enumerate(reserve_lines):
            if i == len(reserve_lines) - 1:
                line_amount = amount - distributed
            else:
                line_amount = round(
                    amount * (rline.amount / total_reserve), 2
                )
                distributed += line_amount

            if line_amount > 0:
                vals = {
                    "commitment_id": self.id,
                    "line_type": "consume",
                    "account_id": rline.account_id.id,
                    "amount": line_amount,
                    "analytic_distribution": rline.analytic_distribution,
                    "description": _("Consumption"),
                    "date": fields.Date.today(),
                }
                lines |= self.env["budget.commitment.line"].create(vals)

        return lines

    def _create_consume_budget_move(self, amount):
        """Backward compat: create consume lines and post them immediately."""
        consume_lines = self._create_consume_lines(amount)
        for line in consume_lines:
            line.post_line()
        return consume_lines.mapped("budget_move_id")

    def close_commitment(self):
        """Close the commitment (mark as done)."""
        self.ensure_one()

        if self.is_closed:
            return

        if not self.is_approved:
            raise UserError(
                _("Cannot close commitment %s - it is not yet approved")
                % self.name
            )

        self.is_closed = True

        _logger.info(
            "Closed budget commitment %s - Released %.2f",
            self.name,
            self.remaining_amount,
        )
