import logging

from odoo import Command, api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class BudgetCommitmentLine(models.Model):
    """Budget Commitment Line - Individual line item within budget commitments."""

    _name = "budget.commitment.line"
    _description = "Budget Commitment Line"
    _order = "sequence, id"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Budget Commitment",
        required=True,
        ondelete="cascade",
        index=True,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("reserved", "Reserved"),
            ("obligated", "Obligated"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Line Status",
        required=True,
        readonly=True,
        copy=False,
        default="draft",
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
    )

    amount = fields.Monetary(
        string="จำนวนเงิน",
        required=True,
        currency_field="currency_id",
    )

    description = fields.Char(
        string="Description",
    )

    # === Analytic Distribution === #

    analytic_distribution = fields.Json(
        string="Analytic Distribution",
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_fields",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_fields",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_fields",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_fields",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
    )

    # === Related from parent === #

    currency_id = fields.Many2one(
        related="commitment_id.currency_id",
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        related="commitment_id.company_id",
        store=True,
        readonly=True,
    )

    parent_state = fields.Selection(
        related="commitment_id.state",
        store=True,
        string="Status",
    )

    account_fiscal_year_id = fields.Many2one(
        related="commitment_id.account_fiscal_year_id",
        store=True,
        readonly=True,
    )

    # === Budget Move Tracking === #

    budget_move_line_ids = fields.One2many(
        comodel_name="budget.move.line",
        inverse_name="commitment_line_id",
        string="Related Budget Move Lines",
        readonly=True,
    )

    # === Computed Fields === #

    consumed_amount = fields.Monetary(
        string="Consumed",
        compute="_compute_consumed_amount",
        store=True,
        currency_field="currency_id",
    )

    remaining_amount = fields.Monetary(
        string="Remaining",
        compute="_compute_remaining_amount",
        store=True,
        currency_field="currency_id",
    )

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

    # === Analytic Computation === #

    @api.depends("analytic_distribution")
    def _compute_analytic_fields(self):
        """Compute 4D analytic fields from distribution JSON."""
        for line in self:
            line.activity_analytic_id = False
            line.department_analytic_id = False
            line.fund_analytic_id = False
            line.source_analytic_id = False

            if line.analytic_distribution:
                analytic_ids = [
                    int(aid)
                    for aid in line.analytic_distribution.keys()
                    if str(aid).isdigit()
                ]
                if analytic_ids:
                    analytics = self.env["account.analytic.account"].browse(
                        analytic_ids
                    )
                    for aa in analytics.exists():
                        code = aa.root_plan_id.code
                        if code == "activities":
                            line.activity_analytic_id = aa
                        elif code == "departments":
                            line.department_analytic_id = aa
                        elif code == "funds":
                            line.fund_analytic_id = aa
                        elif code == "sources":
                            line.source_analytic_id = aa

    def _update_analytic_distribution(self):
        """Update analytic distribution JSON from individual fields."""
        self.ensure_one()
        distribution = {}
        for account in [
            self.activity_analytic_id,
            self.department_analytic_id,
            self.fund_analytic_id,
            self.source_analytic_id,
        ]:
            if account:
                distribution[str(account.id)] = 100.0
        self.analytic_distribution = distribution if distribution else False

    def _inverse_activity_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_department_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_fund_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_source_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    # === Consumption Tracking === #

    @api.depends(
        "amount",
        "budget_move_line_ids.balance",
        "budget_move_line_ids.parent_state",
        "commitment_id.budget_move_ids.state",
        "commitment_id.budget_move_ids.line_ids.balance",
    )
    def _compute_consumed_amount(self):
        """Calculate consumed amount from linked budget move lines."""
        for line in self:
            consumed = 0.0

            # Primary: Use direct link via commitment_line_id
            posted_move_lines = line.budget_move_line_ids.filtered(
                lambda ml: ml.parent_state == "posted"
            )
            if posted_move_lines:
                consumed = sum(abs(ml.balance) for ml in posted_move_lines)
            elif len(line.commitment_id.line_ids) == 1:
                # Fallback for legacy data: single-line commitment with header-level moves
                for move in line.commitment_id.budget_move_ids.filtered(
                    lambda m: m.state == "posted"
                ):
                    consumed += sum(abs(ml.balance) for ml in move.line_ids)

            line.consumed_amount = min(consumed, line.amount) if line.amount else 0.0

    @api.depends("amount", "consumed_amount")
    def _compute_remaining_amount(self):
        for line in self:
            line.remaining_amount = line.amount - line.consumed_amount

    # === Budget Availability === #

    @api.depends(
        "account_id",
        "analytic_distribution",
        "account_fiscal_year_id",
        "amount",
        "state",
    )
    def _compute_available_budget(self):
        """Calculate real-time budget availability for this line."""
        budget_controller = self.env["budget.controller"]

        for line in self:
            if not all(
                [
                    line.account_id,
                    line.activity_analytic_id,
                    line.fund_analytic_id,
                    line.account_fiscal_year_id,
                ]
            ):
                line.available_budget_amount = 0.0
                line.budget_availability_status = "insufficient"
                line.budget_availability_percentage = 0.0
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
                    line.source_analytic_id.id if line.source_analytic_id else False
                ),
            }

            try:
                available = budget_controller.get_available_budget(
                    analytic_data,
                    line.account_fiscal_year_id.id,
                    line.company_id.id,
                )

                # If already reserved/obligated, add back own remaining amount
                if line.state in ["reserved", "obligated"] and line.remaining_amount:
                    available += line.remaining_amount

                line.available_budget_amount = available

                if line.amount:
                    allow_negative = (
                        self.env["ir.config_parameter"]
                        .sudo()
                        .get_param("budget.allow_negative", False)
                    )

                    if available >= line.amount:
                        line.budget_availability_status = "sufficient"
                    elif available >= line.amount * 0.5 or (
                        allow_negative and available >= 0
                    ):
                        line.budget_availability_status = "warning"
                    elif allow_negative:
                        line.budget_availability_status = "warning"
                    else:
                        line.budget_availability_status = "insufficient"

                    line.budget_availability_percentage = (
                        (line.amount / available * 100) if available > 0 else 999.99
                    )
                else:
                    line.budget_availability_status = "sufficient"
                    line.budget_availability_percentage = 0.0

            except Exception as e:
                _logger.warning(
                    "Error calculating budget for commitment line %s: %s",
                    line.id,
                    str(e),
                )
                line.available_budget_amount = 0.0
                line.budget_availability_status = "insufficient"
                line.budget_availability_percentage = 0.0

    # === Consume === #

    def consume(self, amount):
        """Consume budget from this specific line."""
        self.ensure_one()

        if self.state not in ["reserved", "obligated"]:
            raise UserError(
                _("Can only consume from reserved or obligated lines")
            )

        if amount > self.remaining_amount:
            raise ValidationError(
                _("Cannot consume %.2f - only %.2f remaining in this line")
                % (amount, self.remaining_amount)
            )

        return self._create_consume_budget_move(amount)

    def _prepare_consume_line_vals(self, amount):
        """Prepare budget.move.line vals for consuming from this line."""
        return {
            "account_id": self.account_id.id,
            "balance": -amount,
            "commitment_line_id": self.id,
            "activity_analytic_id": self.activity_analytic_id.id,
            "department_analytic_id": (
                self.department_analytic_id.id
                if self.department_analytic_id
                else False
            ),
            "fund_analytic_id": self.fund_analytic_id.id,
            "source_analytic_id": (
                self.source_analytic_id.id if self.source_analytic_id else False
            ),
        }

    def _create_consume_budget_move(self, amount):
        """Create a budget move to consume from this line."""
        commitment = self.commitment_id
        move_vals = {
            "name": _("Consumption of %s") % commitment.name,
            "date": fields.Date.today(),
            "account_fiscal_year_id": commitment.account_fiscal_year_id.id,
            "commitment_id": commitment.id,
            "move_type": "consume",
            "line_ids": [Command.create(self._prepare_consume_line_vals(amount))],
        }
        budget_move = self.env["budget.move"].create(move_vals)
        budget_move.action_post()
        return budget_move

    # === Line-Level Workflow === #

    def action_reserve(self):
        for line in self:
            if line.state != "draft":
                raise UserError(_("Only draft lines can be reserved."))
            line.state = "reserved"

    def action_obligate(self):
        for line in self:
            if line.state == "obligated":
                continue
            if line.state != "reserved":
                raise UserError(_("Line must be in reserved state to obligate."))
            line.state = "obligated"

    def action_done(self):
        for line in self:
            if line.state == "done":
                continue
            if line.state != "obligated":
                raise UserError(_("Line must be in obligated state to mark as done."))
            line.state = "done"

    def action_cancel(self):
        for line in self:
            if line.state == "cancel":
                continue
            if line.state == "done":
                raise UserError(_("Cannot cancel a done line."))
            line.state = "cancel"

    def action_reset_to_draft(self):
        for line in self:
            if line.state != "cancel":
                raise UserError(_("Only cancelled lines can be reset to draft."))
            line.state = "draft"

    # === Constraints === #

    @api.constrains("amount")
    def _check_positive_amount(self):
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_("Line amount must be positive."))
