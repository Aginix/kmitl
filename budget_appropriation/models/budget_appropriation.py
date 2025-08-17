import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    """
    Budget Appropriation - Draft appropriations before creating budget moves.

    Business Purpose:
        Budget appropriations serve as draft budget allocations that can be
        reviewed and modified before being posted as budget moves. This provides
        a preliminary stage for budget planning without affecting the actual
        budget accounts through double-entry accounting.

    Key Differences from Budget Move:
        • No double-entry accounting - simple appropriation tracking
        • Can be extensively modified in draft state
        • Creates budget moves only after approval
        • Focuses on appropriation planning rather than accounting entries

    State Lifecycle:
        draft → review → posted → cancel
        │       │        │        │
        │       │        │        └── Cancelled, no budget impact
        │       │        └─────────── Creates budget.move entries
        │       └──────────────────── Under approval, locked from changes
        └──────────────────────────── Editable, no budget impact

    Integration with Budget System:
        • Creates budget.move entries when posted
        • Maintains link to created budget moves
        • Provides appropriation history and audit trail
    """

    _name = "budget.appropriation"
    _description = "Budget Appropriation"
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
    ref = fields.Char(
        string="Reference",
        copy=False,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
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
    line_ids = fields.One2many(
        comodel_name="budget.appropriation.line",
        inverse_name="appropriation_id",
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
        related="journal_id.default_budget_type",
        string="Budget Type",
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
    total_amount = fields.Float(
        string="Total Amount",
        compute="_compute_amount",
        readonly=True,
        store=True,
        digits="Budget Precision",
    )

    # Link to created budget move
    budget_move_id = fields.Many2one(
        comodel_name="budget.move",
        string="Created Budget Move",
        readonly=True,
        copy=False,
        help="Budget move created when this appropriation was posted",
    )

    # Display buttons
    show_reset_to_draft_button = fields.Boolean(
        compute="_compute_show_reset_to_draft_button"
    )
    hide_post_button = fields.Boolean(
        compute="_compute_hide_post_button", readonly=True
    )
    hide_review_button = fields.Boolean(
        compute="_compute_hide_review_button", readonly=True
    )

    @api.depends("line_ids.balance")
    def _compute_amount(self):
        for appropriation in self:
            appropriation.total_amount = sum(appropriation.line_ids.mapped("balance"))

    @api.depends("state", "date")
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or "", m.id))

        for appropriation in self:
            if appropriation.state == "cancel":
                continue

            appropriation_has_name = appropriation.name and appropriation.name != "New"
            if appropriation_has_name or (appropriation.state not in ("review", "posted")):
                continue
            if not appropriation_has_name and appropriation.date:
                appropriation.name = self.env["ir.sequence"].next_by_code("budget.appropriation") or _("New")

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
                "cancel",
            )

    def action_review(self):
        self.write({"state": "review"})

    def action_post(self):
        """Post appropriation and create budget move"""
        self._create_budget_move()
        self.write({"state": "posted"})

    def button_cancel(self):
        self.write({"state": "cancel"})

    def button_draft(self):
        # Reset to draft only if no budget move created
        for record in self:
            if record.budget_move_id and record.budget_move_id.state == "posted":
                raise UserError(_("Cannot reset to draft: Related budget move is already posted."))
        self.write({"state": "draft"})

    def _create_budget_move(self):
        """Create budget move from appropriation"""
        for appropriation in self:
            if appropriation.budget_move_id:
                continue  # Already created

            # Create budget move
            move_vals = {
                "move_type": "appropriation",
                "date": appropriation.date,
                "ref": appropriation.ref,
                "journal_id": appropriation.journal_id.id,
                "department_analytic_id": appropriation.department_analytic_id.id,
                "source_analytic_id": appropriation.source_analytic_id.id,
                "date_range_fy_id": appropriation.date_range_fy_id.id,
                "note": appropriation.note,
                "company_id": appropriation.company_id.id,
                "currency_id": appropriation.currency_id.id,
                "line_ids": [],
            }

            # Create move lines
            for line in appropriation.line_ids:
                line_vals = {
                    "account_id": line.account_id.id,
                    "balance": line.balance,
                    "note": line.note,
                }
                # Add analytic distribution
                if line.analytic_distribution:
                    line_vals["analytic_distribution"] = line.analytic_distribution

                move_vals["line_ids"].append((0, 0, line_vals))

            budget_move = self.env["budget.move"].create(move_vals)
            appropriation.budget_move_id = budget_move.id

            # Auto-post the budget move
            budget_move.action_review()
            budget_move.action_post()

    def action_open_f5_preview(self):
        """Open the budget appropriation F5 preview in full screen"""
        self.ensure_one()
        return {
            "name": _("Budget Appropriation F5 Preview"),
            "type": "ir.actions.client",
            "tag": "budget_appropriation_f5_preview",
            "target": "current",
            "res_id": self.id,
            "res_model": "budget.appropriation",
            "context": {
                "active_id": self.id,
                "active_model": "budget.appropriation",
            },
        }