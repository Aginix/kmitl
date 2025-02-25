import logging

from odoo import api, fields, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _name = "budget.appropriation"
    _description = "Budget Appropriation"
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
    template_id = fields.Many2one(
        comodel_name="budget.template",
        index=True,
        ondelete="cascade",
        copy=False,
        domain="[('date_range_fy_id', '=', date_range_fy_id)]",
    )
    active = fields.Boolean(default=True)
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
        comodel_name="budget.appropriation.line",
        inverse_name="appropriation_id",
        copy=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.model
    def _search_date_range_fy(self, operator, value):
        if operator in ("=", "!=", "in", "not in"):
            date_range_domain = [("id", operator, value)]
        else:
            date_range_domain = [("name", operator, value)]

        date_ranges = self.env["account.fiscal.year"].search(date_range_domain)

        domain = [("id", "=", -1)]
        for date_range in date_ranges:
            domain = expression.OR(
                [
                    domain,
                    [
                        "&",
                        ("date", ">=", date_range.date_from),
                        ("date", "<=", date_range.date_to),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", date_range.company_id.id),
                    ],
                ]
            )
        return domain

    @api.depends("date", "state")
    def _compute_hide_post_button(self):
        for record in self:
            record.hide_post_button = record.state != "draft"

    @api.depends("state")
    def _compute_show_reset_to_draft_button(self):
        for record in self:
            record.show_reset_to_draft_button = record.state in ("posted", "cancel")

    def action_post(self):
        self.write({"state": "posted"})

    def button_cancel(self):
        self.write({"state": "cancel"})

    def button_draft(self):
        self.write({"state": "draft"})


class BudgetAppropriationLine(models.Model):
    _name = "budget.appropriation.line"
    _description = "Budget Appropriation Line"
    _inherit = ["analytic.distribution.mixin"]

    appropriation_id = fields.Many2one(
        comodel_name="budget.appropriation",
        string="Budget Appropriation",
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )

    template_id = fields.Many2one(
        related="appropriation_id.template_id", store=True, readonly=True
    )
    template_line_id = fields.Many2one(
        comodel_name="budget.template.line",
        index=True,
    )
    budget_type = fields.Selection(
        related="template_line_id.template_id.budget_type", store=True, readonly=True
    )
    amount = fields.Float(
        required=True,
        digits="Budget Precision",
        help="Amount",
    )
    credit = fields.Float(
        readonly=True,
        digits="Budget Precision",
    )
    debit = fields.Float(
        readonly=True,
        digits="Budget Precision",
    )
    note = fields.Char(tracking=True)

    # === Parent fields === #
    name = fields.Char(
        related="appropriation_id.name", store=True, index="btree", readonly=True
    )
    date_range_fy_id = fields.Many2one(
        related="appropriation_id.date_range_fy_id", store=True
    )
    parent_state = fields.Selection(related="appropriation_id.state", store=True)
    source_analytic_id = fields.Many2one(
        related="appropriation_id.source_analytic_id", store=True
    )

    @api.depends("amount")
    def _compute_amount(self):
        pass
