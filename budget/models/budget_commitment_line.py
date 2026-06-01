import logging

from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

PROTECTED_FIELDS = {
    "amount",
    "account_id",
    "move_type",
    "analytic_distribution",
    "activity_analytic_id",
    "fund_analytic_id",
}


class BudgetCommitmentLine(models.Model):
    """Budget Commitment Line - Ledger entry for budget operations.

    Each line represents a budget transaction:
    - reserve: จองงบประมาณ (positive = จอง, negative = คืนจอง)
    - obligate: ผูกพันงบประมาณ (positive = ผูกพัน, negative = คืนผูกพัน)
    - consume: ตัดงบประมาณ (positive = ตัดงบ, negative = คืนเงิน)

    Posted lines are immutable — cancel instead of edit/delete.
    Consume lines auto-create a budget.move for accounting integration.
    """

    _name = "budget.commitment.line"
    _description = "Budget Commitment Line"
    _inherit = ["analytic.mixin", "mail.thread"]
    _order = "sequence, id"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Commitment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        required=True,
    )
    name = fields.Char(string="Description")
    move_type = fields.Selection(
        selection=[
            ("reserve", "จองงบ"),
            ("obligate", "ผูกพัน"),
            ("consume", "ตัดงบ"),
        ],
        string="Type",
        required=True,
        default="reserve",
        tracking=True,
    )
    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
    )
    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field="currency_id",
        help="Positive = forward (reserve/obligate/consume), Negative = reversal",
    )
    state = fields.Selection(
        selection=[
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        default="posted",
        tracking=True,
    )

    # Source document reference (e.g. purchase.request, purchase.order)
    res_model = fields.Char(
        string="Source Model",
        index=True,
        readonly=True,
    )
    res_id = fields.Many2oneReference(
        string="Source Document",
        model_field="res_model",
        index=True,
        readonly=True,
    )
    res_name = fields.Char(
        string="Source Name",
        compute="_compute_res_name",
    )

    # Link to auto-created budget.move (for consume lines)
    budget_move_id = fields.Many2one(
        comodel_name="budget.move",
        string="Budget Move",
        readonly=True,
        index=True,
        ondelete="set null",
    )

    # Analytic convenience fields (line-level: activity + fund only)
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "funds": "fund_analytic_id",
    }

    def _inverse_activity_analytic(self):
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_fund_analytic(self):
        for line in self:
            line._update_analytic_distribution("funds")

    # Related from header
    department_analytic_id = fields.Many2one(
        related="commitment_id.department_analytic_id",
        store=True,
        string="ส่วนงาน",
    )
    source_analytic_id = fields.Many2one(
        related="commitment_id.source_analytic_id",
        store=True,
        string="แหล่งเงิน",
    )
    currency_id = fields.Many2one(related="commitment_id.currency_id")
    company_id = fields.Many2one(
        related="commitment_id.company_id",
        store=True,
    )
    account_fiscal_year_id = fields.Many2one(
        related="commitment_id.account_fiscal_year_id",
        store=True,
        string="ปีงบประมาณ",
    )

    @api.depends("res_model", "res_id")
    def _compute_res_name(self):
        for line in self:
            if line.res_model and line.res_id:
                record = self.env[line.res_model].browse(line.res_id).exists()
                line.res_name = record.display_name if record else False
            else:
                line.res_name = False

    def action_open_source_document(self):
        """Open the source document that created this line."""
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }

    # --- Constraints ---

    @api.constrains("amount", "move_type", "state")
    def _check_commitment_limits(self):
        """Enforce cascade constraints: reserved <= cap, obligated <= reserved, consumed <= obligated"""
        commitments = self.mapped("commitment_id")
        for commitment in commitments:
            posted = commitment.line_ids.filtered(lambda l: l.state == "posted")
            total_reserved = sum(
                posted.filtered(lambda l: l.move_type == "reserve").mapped("amount")
            )
            total_obligated = sum(
                posted.filtered(lambda l: l.move_type == "obligate").mapped("amount")
            )
            total_consumed = sum(
                posted.filtered(lambda l: l.move_type == "consume").mapped("amount")
            )

            if commitment.amount and total_reserved > commitment.amount:
                raise ValidationError(
                    _(
                        "Total reserved (%(reserved).2f) exceeds commitment cap (%(cap).2f)"
                    )
                    % {"reserved": total_reserved, "cap": commitment.amount}
                )
            if total_obligated > total_reserved:
                raise ValidationError(
                    _(
                        "Total obligated (%(obligated).2f) exceeds total reserved (%(reserved).2f)"
                    )
                    % {"obligated": total_obligated, "reserved": total_reserved}
                )
            if total_consumed > total_obligated:
                raise ValidationError(
                    _(
                        "Total consumed (%(consumed).2f) exceeds total obligated (%(obligated).2f)"
                    )
                    % {"consumed": total_consumed, "obligated": total_obligated}
                )

            # B2: over-reversal must never drive a net total below zero.
            if total_reserved < 0:
                raise ValidationError(
                    _("Total reserved cannot be negative (%.2f).") % total_reserved
                )
            if total_obligated < 0:
                raise ValidationError(
                    _("Total obligated cannot be negative (%.2f).") % total_obligated
                )
            if total_consumed < 0:
                raise ValidationError(
                    _("Total consumed cannot be negative (%.2f).") % total_consumed
                )

    # --- Immutability ---

    def write(self, vals):
        if PROTECTED_FIELDS & set(vals):
            posted = self.filtered(lambda l: l.state == "posted")
            if posted:
                raise UserError(
                    _("Cannot edit posted ledger lines. Cancel and create a new entry instead.")
                )
        return super().write(vals)

    def unlink(self):
        posted = self.filtered(lambda l: l.state == "posted")
        if posted:
            raise UserError(
                _("Cannot delete posted ledger lines. Cancel them instead.")
            )
        return super().unlink()

    # --- Actions ---

    def action_cancel(self):
        for line in self:
            if line.state == "cancel":
                continue
            line.state = "cancel"
            # Cascade cancel to linked budget.move
            if line.budget_move_id and line.budget_move_id.state != "cancel":
                line.budget_move_id.button_cancel()
        # Re-derive header state band (e.g. partial -> reserved once every
        # obligate/consume line is cancelled).
        self.mapped("commitment_id")._sync_state()

    def action_post(self):
        for line in self:
            if line.state != "posted":
                line.state = "posted"

    # --- Budget Move Creation ---

    def _prepare_budget_move_vals(self):
        """Prepare budget.move values for a consume line."""
        self.ensure_one()
        commitment = self.commitment_id
        return {
            "name": _("New"),
            "date": self.date,
            "move_type": "consume",
            "budget_type": "expense",
            "account_fiscal_year_id": commitment.account_fiscal_year_id.id,
            "department_analytic_id": (
                self.department_analytic_id.id
                if self.department_analytic_id
                else False
            ),
            "source_analytic_id": (
                self.source_analytic_id.id
                if self.source_analytic_id
                else False
            ),
            "company_id": commitment.company_id.id,
            "currency_id": commitment.currency_id.id,
            "commitment_id": commitment.id,
            "commitment_line_id": self.id,
            "line_ids": [Command.create(self._prepare_budget_move_line_vals())],
        }

    def _prepare_budget_move_line_vals(self):
        """Prepare budget.move.line values for consumption."""
        self.ensure_one()
        return {
            "account_id": self.account_id.id,
            "balance": -self.amount,
            "analytic_distribution": self.analytic_distribution,
        }

    def _create_budget_move(self):
        """Create and post a budget.move for a consume line."""
        self.ensure_one()
        move_vals = self._prepare_budget_move_vals()
        budget_move = self.env["budget.move"].create(move_vals)
        budget_move.action_review()
        budget_move.action_post()
        self.budget_move_id = budget_move
        _logger.info(
            "Created budget move %s for consume line %s",
            budget_move.name,
            self.id,
        )
        return budget_move

    # --- CRUD ---

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        # B1: forward obligate/consume are only allowed on an active commitment.
        # Exempt are reserve lines (created with the header while still draft) and
        # reversal lines (negative amount — refunds / de-obligations, which must
        # stay postable even after a commitment is fully consumed/"done");
        # _sync_state re-derives the state band once a reversal lands.
        blocked = lines.filtered(
            lambda l: l.state == "posted"
            and l.move_type in ("obligate", "consume")
            and l.amount > 0
            and l.commitment_id.state not in ("reserved", "partial")
        )
        if blocked:
            raise UserError(
                _(
                    "Can only obligate or consume a commitment that is "
                    "reserved or in progress."
                )
            )

        # Auto-create budget.move for consume lines
        for line in lines.filtered(
            lambda l: l.state == "posted" and l.move_type == "consume"
        ):
            line._create_budget_move()

        # Re-derive the header state band (reserved/partial/done) from the
        # updated line totals.
        lines.mapped("commitment_id")._sync_state()

        return lines
