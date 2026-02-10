import logging
from odoo import Command, api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

# Fields that should be extracted from header vals into a commitment line
_LINE_FIELDS = [
    "account_id",
    "amount",
    "activity_analytic_id",
    "department_analytic_id",
    "fund_analytic_id",
    "source_analytic_id",
    "analytic_distribution",
]


class BudgetCommitment(models.Model):
    """
    Budget Commitment - Reserve budget amounts before consumption.

    Implements a header-line architecture where each commitment can have
    one or more lines, each targeting a specific budget account and
    analytic combination.

    State Lifecycle:
        draft → reserved → obligated → done
                                      ↗
        cancel ← (any non-done state)
    """

    _name = "budget.commitment"
    _description = "Budget Commitment"
    _inherit = ["analytic.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "ref"]

    READONLY_STATES = {
        "reserved": [("readonly", True)],
        "obligated": [("readonly", True)],
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

    _STATE_PRIORITY = {
        "draft": 0,
        "reserved": 1,
        "obligated": 2,
        "done": 3,
    }

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("reserved", "Reserved"),
            ("obligated", "Obligated"),
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
        states=READONLY_STATES,
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
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
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

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    def _inverse_activity_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("activities")

    def _inverse_department_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("departments")

    def _inverse_fund_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("funds")

    def _inverse_source_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("sources")

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

    # === Budget Availability (aggregated from lines) === #

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

    # === Compute: State from Lines === #

    @api.depends("line_ids.state")
    def _compute_state(self):
        """Compute header state from line states (least advanced non-cancelled)."""
        for rec in self:
            lines = rec.line_ids
            if not lines:
                rec.state = "draft"
                continue

            active_lines = lines.filtered(lambda l: l.state != "cancel")
            if not active_lines:
                rec.state = "cancel"
                continue

            rec.state = min(
                active_lines.mapped("state"),
                key=lambda s: self._STATE_PRIORITY.get(s, 0),
            )

    # === Compute: Header from Lines === #

    @api.depends(
        "line_ids.account_id",
        "line_ids.amount",
        "line_ids.analytic_distribution",
    )
    def _compute_header_from_lines(self):
        """Compute header fields from first/all lines for backward compat."""
        for rec in self:
            first_line = rec.line_ids[:1]
            rec.account_id = first_line.account_id
            rec.amount = sum(rec.line_ids.mapped("amount"))
            rec.analytic_distribution = first_line.analytic_distribution or False

    def _inverse_account_id(self):
        """When header account_id is set, apply to first line."""
        for rec in self:
            if len(rec.line_ids) == 1:
                rec.line_ids.account_id = rec.account_id

    def _inverse_amount(self):
        """When header amount is set, apply to first line."""
        for rec in self:
            if len(rec.line_ids) == 1:
                rec.line_ids.amount = rec.amount

    def _inverse_analytic_distribution(self):
        """When header analytic_distribution is set, apply to first line."""
        for rec in self:
            if len(rec.line_ids) == 1:
                rec.line_ids.analytic_distribution = rec.analytic_distribution

    # === Compute: Consumed / Remaining === #

    @api.depends("line_ids.consumed_amount")
    def _compute_consumed_amount(self):
        for record in self:
            record.consumed_amount = sum(record.line_ids.mapped("consumed_amount"))

    @api.depends("amount", "consumed_amount")
    def _compute_remaining_amount(self):
        for record in self:
            record.remaining_amount = record.amount - record.consumed_amount

    # === Compute: Budget Availability (aggregated from lines) === #

    @api.depends(
        "line_ids.available_budget_amount",
        "line_ids.budget_availability_status",
        "line_ids.budget_availability_percentage",
    )
    def _compute_available_budget(self):
        """Aggregate budget availability from lines."""
        status_priority = {"insufficient": 0, "warning": 1, "sufficient": 2}

        for record in self:
            lines = record.line_ids
            if not lines:
                record.available_budget_amount = 0.0
                record.budget_availability_status = "insufficient"
                record.budget_availability_percentage = 0.0
                continue

            record.available_budget_amount = sum(
                lines.mapped("available_budget_amount")
            )

            # Worst status across lines
            statuses = lines.mapped("budget_availability_status")
            worst = min(
                (s for s in statuses if s),
                key=lambda s: status_priority.get(s, 2),
                default="insufficient",
            )
            record.budget_availability_status = worst

            # Max percentage across lines
            percentages = lines.mapped("budget_availability_percentage")
            record.budget_availability_percentage = max(percentages) if percentages else 0.0

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

    @api.onchange("amount", "account_id", "activity_analytic_id", "fund_analytic_id")
    def _onchange_check_budget_availability(self):
        if self.amount and self.available_budget_amount >= 0:
            allow_negative = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("budget.allow_negative", False)
            )

            if self.budget_availability_status == "insufficient" and not allow_negative:
                return {
                    "warning": {
                        "title": _("Insufficient Budget"),
                        "message": _(
                            "The requested amount (%(requested)s) exceeds the available budget (%(available)s).\n\n"
                            "Budget Account: %(account)s\n"
                            "Activity: %(activity)s\n"
                            "Fund: %(fund)s\n\n"
                            "Please reduce the amount or select a different analytic combination."
                        )
                        % {
                            "requested": "{:,.2f}".format(self.amount),
                            "available": "{:,.2f}".format(self.available_budget_amount),
                            "account": (
                                self.account_id.display_name
                                if self.account_id
                                else "N/A"
                            ),
                            "activity": (
                                self.activity_analytic_id.display_name
                                if self.activity_analytic_id
                                else "N/A"
                            ),
                            "fund": (
                                self.fund_analytic_id.display_name
                                if self.fund_analytic_id
                                else "N/A"
                            ),
                        },
                    }
                }
            elif self.budget_availability_status == "warning":
                if allow_negative and self.available_budget_amount < self.amount:
                    return {
                        "warning": {
                            "title": _("Negative Budget Warning"),
                            "message": _(
                                "This commitment will create a negative budget balance.\n\n"
                                "Requested: %(requested)s\n"
                                "Available: %(available)s\n"
                                "Remaining after commitment: %(remaining)s\n\n"
                                "Negative budgets are allowed by system configuration."
                            )
                            % {
                                "requested": "{:,.2f}".format(self.amount),
                                "available": "{:,.2f}".format(
                                    self.available_budget_amount
                                ),
                                "remaining": "{:,.2f}".format(
                                    self.available_budget_amount - self.amount
                                ),
                            },
                        }
                    }
                else:
                    return {
                        "warning": {
                            "title": _("Low Budget Warning"),
                            "message": _(
                                "This commitment will use %(percentage).1f%% of the available budget.\n\n"
                                "Requested: %(requested)s\n"
                                "Available: %(available)s\n"
                                "Remaining after commitment: %(remaining)s"
                            )
                            % {
                                "percentage": self.budget_availability_percentage,
                                "requested": "{:,.2f}".format(self.amount),
                                "available": "{:,.2f}".format(
                                    self.available_budget_amount
                                ),
                                "remaining": "{:,.2f}".format(
                                    self.available_budget_amount - self.amount
                                ),
                            },
                        }
                    }

    # === Create Override (old API compat) === #

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create a commitment line from old-style header vals."""
        analytic_id_fields = [
            "activity_analytic_id",
            "department_analytic_id",
            "fund_analytic_id",
            "source_analytic_id",
        ]
        for vals in vals_list:
            if "line_ids" not in vals and vals.get("account_id"):
                line_vals = {}
                for field in _LINE_FIELDS:
                    if field in vals:
                        line_vals[field] = vals.pop(field)

                # Build analytic_distribution from 4D IDs if not already present
                if "analytic_distribution" not in line_vals:
                    distribution = {}
                    for field in analytic_id_fields:
                        aid = line_vals.pop(field, False)
                        if aid:
                            distribution[str(aid)] = 100.0
                    line_vals["analytic_distribution"] = distribution or False
                else:
                    # Remove 4D fields from line_vals (they're non-stored computed)
                    for field in analytic_id_fields:
                        line_vals.pop(field, None)

                vals["line_ids"] = [Command.create(line_vals)]
        return super().create(vals_list)

    # === Workflow Methods === #

    def action_check_budget_availability(self):
        """Check budget availability for all lines."""
        self.ensure_one()

        if not self.line_ids:
            raise UserError(_("Commitment must have at least one line."))

        # Trigger recomputation
        self.line_ids._compute_available_budget()

        insufficient_lines = self.line_ids.filtered(
            lambda l: l.budget_availability_status == "insufficient"
        )
        if insufficient_lines:
            messages = []
            for line in insufficient_lines:
                messages.append(
                    _("• %s: Requested %s, Available %s")
                    % (
                        line.account_id.display_name,
                        "{:,.2f}".format(line.amount),
                        "{:,.2f}".format(line.available_budget_amount),
                    )
                )
            raise UserError(
                _("Insufficient budget for the following lines:\n\n%s")
                % "\n".join(messages)
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

    def action_reserve(self):
        """Reserve all draft lines."""
        for record in self:
            draft_lines = record.line_ids.filtered(lambda l: l.state == "draft")
            if not draft_lines:
                raise UserError(_("No draft lines to reserve."))

            record.action_check_budget_availability()

            if record.name == _("New"):
                record.name = self.env["ir.sequence"].next_by_code(
                    "budget.commitment"
                ) or _("New")

            draft_lines.action_reserve()

    def action_obligate(self):
        """Obligate all reserved lines."""
        for record in self:
            reserved_lines = record.line_ids.filtered(lambda l: l.state == "reserved")
            if not reserved_lines:
                if all(l.state in ("obligated", "done") for l in record.line_ids):
                    continue
                raise UserError(
                    _("Cannot obligate commitment %s - no reserved lines found")
                    % record.name
                )
            reserved_lines.action_obligate()
            _logger.info("Obligated budget commitment %s", record.name)

    def action_obligate_lines(self, line_ids=None):
        """Obligate specific lines by ID."""
        self.ensure_one()
        if line_ids:
            lines = self.line_ids.filtered(lambda l: l.id in line_ids)
        else:
            lines = self.line_ids.filtered(lambda l: l.state == "reserved")
        if not lines:
            raise UserError(_("No lines found to obligate."))
        lines.action_obligate()

    def action_done(self):
        """Mark all obligated lines as done."""
        for record in self:
            record.close_commitment()

    def action_cancel(self):
        """Cancel all non-done lines."""
        for record in self:
            cancellable = record.line_ids.filtered(
                lambda l: l.state not in ("done", "cancel")
            )
            if not cancellable:
                if all(l.state == "cancel" for l in record.line_ids):
                    continue
                raise UserError(
                    _("Cannot cancel commitment %s - it is already done") % record.name
                )
            cancellable.action_cancel()
            _logger.info("Cancelled budget commitment %s", record.name)

    def action_reset_to_draft(self):
        """Reset all cancelled lines to draft."""
        for record in self:
            non_cancelled = record.line_ids.filtered(lambda l: l.state != "cancel")
            if non_cancelled:
                raise UserError(_("Only fully cancelled commitments can be reset to draft."))
            record.line_ids.action_reset_to_draft()

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

    # === Consume (proportional distribution) === #

    def consume(self, amount):
        """Consume budget proportionally across all lines with remaining balance."""
        self.ensure_one()

        active_lines = self.line_ids.filtered(
            lambda l: l.state in ("reserved", "obligated")
        )
        if not active_lines:
            raise UserError(
                _("Can only consume from reserved or obligated commitments")
            )

        if amount > self.remaining_amount:
            raise ValidationError(
                _("Cannot consume %.2f - only %.2f remaining in commitment")
                % (amount, self.remaining_amount)
            )

        budget_move = self._create_consume_budget_move(amount)

        _logger.info(
            "Consumed %.2f from commitment %s (%.2f remaining)",
            amount,
            self.name,
            self.remaining_amount,
        )

        return budget_move

    def _prepare_consume_budget_move_vals(self, amount):
        """Prepare budget.move vals with proportional distribution across lines."""
        lines_with_remaining = self.line_ids.filtered(
            lambda l: l.remaining_amount > 0 and l.state in ("reserved", "obligated")
        )

        if not lines_with_remaining:
            raise UserError(_("No remaining budget to consume in any line."))

        total_remaining = sum(lines_with_remaining.mapped("remaining_amount"))
        move_line_vals = []
        distributed = 0.0

        for i, line in enumerate(lines_with_remaining):
            if i == len(lines_with_remaining) - 1:
                # Last line gets the remainder to avoid rounding issues
                line_amount = amount - distributed
            else:
                line_amount = round(
                    amount * (line.remaining_amount / total_remaining), 2
                )
                distributed += line_amount

            if line_amount > 0:
                move_line_vals.append(
                    Command.create(line._prepare_consume_line_vals(line_amount))
                )

        return {
            "name": _("Consumption of %s") % self.name,
            "date": fields.Date.today(),
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "commitment_id": self.id,
            "move_type": "consume",
            "line_ids": move_line_vals,
        }

    def _prepare_consume_line_vals(self, amount):
        """Backward compat: prepare consume line vals from header (single-line)."""
        if self.line_ids:
            return self.line_ids[0]._prepare_consume_line_vals(amount)
        return {
            "account_id": self.account_id.id,
            "balance": -amount,
            "activity_analytic_id": self.activity_analytic_id.id,
            "department_analytic_id": (
                self.department_analytic_id.id if self.department_analytic_id else False
            ),
            "fund_analytic_id": self.fund_analytic_id.id,
            "source_analytic_id": (
                self.source_analytic_id.id if self.source_analytic_id else False
            ),
        }

    def _create_consume_budget_move(self, amount):
        move_vals = self._prepare_consume_budget_move_vals(amount)
        budget_move = self.env["budget.move"].create(move_vals)
        budget_move.action_post()
        return budget_move

    def close_commitment(self):
        """Close commitment: mark all obligated lines as done."""
        self.ensure_one()

        if self.state == "done":
            return

        obligated_lines = self.line_ids.filtered(lambda l: l.state == "obligated")
        if not obligated_lines:
            raise UserError(
                _("Cannot close commitment %s - no obligated lines found")
                % self.name
            )
        obligated_lines.action_done()

        _logger.info(
            "Closed budget commitment %s - Released %.2f",
            self.name,
            self.remaining_amount,
        )
