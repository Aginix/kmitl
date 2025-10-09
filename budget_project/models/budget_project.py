from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BudgetProject(models.Model):
    _name = "budget.project"
    _description = "Budget Project/Activity"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.distribution.mixin"]
    _order = "create_date desc, id desc"
    _rec_name = "name"

    READONLY_STATES = {
        "validate": [("readonly", True)],
        "in_progress": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        string="ชื่อ",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="รายละเอียด",
        tracking=True,
    )
    amount = fields.Float(
        string="งบประมาณ",
        required=True,
        tracking=True,
        digits="Budget",
    )

    budget_appropriation_id = fields.Many2one(
        "budget.appropriation",
        related="budget_appropriation_line_id.appropriation_id",
        store=True,
        readonly=True,
    )
    budget_appropriation_line_id = fields.Many2one("budget.appropriation.line")
    budget_account_id = fields.Many2one(
        "budget.account", string="รหัสงบประมาณ", states=READONLY_STATES
    )
    activity_analytic_id = fields.Many2one(states=READONLY_STATES)
    department_analytic_id = fields.Many2one(states=READONLY_STATES)
    fund_analytic_id = fields.Many2one(states=READONLY_STATES)
    source_analytic_id = fields.Many2one(states=READONLY_STATES)

    # Additional fields
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("validate", "To Approve"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
    )
    note = fields.Text(
        string="Notes",
    )

    # Related fields for reporting
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        related="budget_appropriation_line_id.account_fiscal_year_id",
        store=True,
        readonly=True,
    )

    @api.constrains("amount")
    def _check_amount(self):
        for project in self:
            if project.amount < 0:
                raise ValidationError(_("Budget amount cannot be negative."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        for project in self:
            if project.state == "done":
                raise ValidationError(_("Cannot delete a completed project."))

    def action_validate(self):
        self.write({"state": "validate"})

    def action_draft(self):
        self.write({"state": "draft"})
