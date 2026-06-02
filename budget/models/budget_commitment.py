import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


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
    _rec_names_search = ["name", "ref"]

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

    # Ledger lines
    line_ids = fields.One2many(
        comodel_name="budget.commitment.line",
        inverse_name="commitment_id",
        string="Ledger Lines",
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

    # Legacy backward-compat fields
    consumed_amount = fields.Monetary(
        string="Consumed Amount",
        compute="_compute_line_totals",
        store=True,
        currency_field="currency_id",
    )
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
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

    @api.depends(
        "line_ids.amount",
        "line_ids.move_type",
        "line_ids.state",
        "amount",
    )
    def _compute_line_totals(self):
        for record in self:
            posted = record.line_ids.filtered(lambda l: l.state == "posted")
            total_reserved = sum(
                posted.filtered(lambda l: l.move_type == "reserve").mapped("amount")
            )
            total_obligated = sum(
                posted.filtered(lambda l: l.move_type == "obligate").mapped("amount")
            )
            total_consumed = sum(
                posted.filtered(lambda l: l.move_type == "consume").mapped("amount")
            )
            record.total_reserved = total_reserved
            record.total_obligated = total_obligated
            record.total_consumed = total_consumed
            record.available_to_obligate = total_reserved - total_obligated
            record.available_to_consume = total_obligated - total_consumed
            # Legacy compat
            record.consumed_amount = total_consumed
            record.remaining_amount = record.amount - total_consumed

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

    @api.constrains("amount")
    def _check_positive_amount(self):
        for record in self:
            if record.amount <= 0:
                raise UserError(_("Commitment cap amount must be positive."))

    # --- Workflow Methods ---

    def action_reserve(self):
        """Draft -> Reserved: validate reserve lines exist"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft commitments can be reserved."))
            if record.total_reserved <= 0:
                raise UserError(
                    _("Cannot reserve: no reserve lines found. Add reserve lines first.")
                )
            if record.name == _("New"):
                record.name = self.env["ir.sequence"].next_by_code(
                    "budget.commitment"
                ) or _("New")
            record.state = "reserved"

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

    def action_view_budget_moves(self):
        """View related budget moves"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Related Budget Moves"),
            "res_model": "budget.move",
            "view_mode": "tree,form",
            "domain": [("commitment_id", "=", self.id)],
            "context": {"default_commitment_id": self.id},
        }
