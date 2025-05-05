import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BudgetMove(models.Model):
    _name = "budget.move"
    _description = "Budget Move"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(tracking=True)

    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        search="_search_date_range_fy",
        tracking=True,
    )
    date = fields.Date(required=True, index=True, tracking=True)
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
    ref = fields.Char(string="Reference", copy=False, tracking=True)
    user_id = fields.Many2one(
        string="Responsible user",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        store=True,
        readonly=False,
    )
    show_reset_to_draft_button = fields.Boolean(
        compute="_compute_show_reset_to_draft_button"
    )
    hide_post_button = fields.Boolean(
        compute="_compute_hide_post_button", readonly=True
    )
    line_ids = fields.One2many(
        comodel_name="budget.move.line",
        inverse_name="move_id",
        copy=True,
        tracking=True,
    )

    @api.depends("date", "state")
    def _compute_hide_post_button(self):
        for record in self:
            record.hide_post_button = record.state != "draft"

    @api.depends("state")
    def _compute_show_reset_to_draft_button(self):
        for move in self:
            move.show_reset_to_draft_button = move.state in ("posted", "cancel")

    def action_post(self):
        self.write({"state": "posted"})

    def button_cancel(self):
        self.write({"state": "cancel"})

    def button_draft(self):
        self.write({"state": "draft"})


class BudgetMoveLine(models.Model):
    _name = "budget.move.line"
    _description = "Budget Move Line"
    _inherit = ["analytic.distribution.mixin"]

    # === Parent fields === #
    move_id = fields.Many2one(
        comodel_name="budget.move",
        string="Budget Move",
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
    parent_state = fields.Selection(related="move_id.state", store=True)
    template_line_id = fields.Many2one(
        comodel_name="budget.template.line",
        index=True,
    )
    template_id = fields.Many2one(related="template_line_id.template_id")
    budget_type = fields.Selection(related="template_line_id.template_id.budget_type")
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

    @api.depends("amount")
    def _compute_amount(self):
        pass
