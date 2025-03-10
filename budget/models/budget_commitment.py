import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    _name = "budget.commitment"
    _description = "Budget Commitment"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()
    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        search="_search_date_range_fy",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date = fields.Date(
        required=True,
        index=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    note = fields.Char(readonly=True, tracking=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
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
    )
    template_id = fields.Many2one(
        comodel_name="budget.template",
        index=True,
        ondelete="cascade",
        copy=False,
        domain="[('date_range_fy_id', '=', date_range_fy_id)]",
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        store=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        domain=[("root_plan_id.code", "=", "departments")],
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        store=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        domain=[("root_plan_id.code", "=", "sources")],
    )
    ref = fields.Char(
        string="Reference",
        copy=False,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    user_id = fields.Many2one(
        string="Responsible user",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        store=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    show_reset_to_draft_button = fields.Boolean(
        compute="_compute_show_reset_to_draft_button"
    )
    hide_post_button = fields.Boolean(
        compute="_compute_hide_post_button", readonly=True
    )
    line_ids = fields.One2many(
        comodel_name="budget.commitment.line",
        inverse_name="commitment_id",
        copy=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.depends("date", "state")
    def _compute_hide_post_button(self):
        for record in self:
            record.hide_post_button = record.state != "draft"

    @api.depends("state")
    def _compute_show_reset_to_draft_button(self):
        for record in self:
            record.show_reset_to_draft_button = record.state in ("submitted", "cancel")

    def action_submit(self):
        self.write({"state": "submitted"})

    def button_cancel(self):
        self.write({"state": "cancel"})

    def button_draft(self):
        self.write({"state": "draft"})
