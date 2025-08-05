from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BudgetProject(models.Model):
    _name = "budget.project"
    _description = "Budget Project/Activity"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.distribution.mixin"]
    _order = "create_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Project/Activity Name",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="Description",
        tracking=True,
    )
    budget_amount = fields.Float(
        string="Budget Amount",
        required=True,
        tracking=True,
        digits="Budget",
    )
    allocated_amount = fields.Float(
        string="Allocated Amount",
        compute="_compute_allocated_amount",
        store=True,
        digits="Budget",
    )
    remaining_amount = fields.Float(
        string="Remaining Amount",
        compute="_compute_remaining_amount",
        store=True,
        digits="Budget",
    )
    
    # Budget integration
    budget_move_line_id = fields.Many2one(
        "budget.move.line",
        string="Budget Move Line",
        ondelete="cascade",
        index=True,
    )
    budget_move_id = fields.Many2one(
        "budget.move",
        string="Budget Move",
        related="budget_move_line_id.move_id",
        store=True,
        readonly=True,
    )
    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        required=True,
        domain="[('project_enabled', '=', True)]",
        tracking=True,
    )
    
    # Financial dimensions - inherited from AnalyticDistributionMixin
    # department_analytic_id, activity_analytic_id, fund_analytic_id, source_analytic_id
    
    # Additional fields
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    date_from = fields.Date(
        string="Start Date",
        tracking=True,
    )
    date_to = fields.Date(
        string="End Date",
        tracking=True,
    )
    responsible_user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
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
    date_range_fy_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        related="budget_move_line_id.date_range_fy_id",
        store=True,
        readonly=True,
    )

    @api.depends("budget_move_line_id", "budget_move_line_id.allocated")
    def _compute_allocated_amount(self):
        for project in self:
            if project.budget_move_line_id:
                # Get allocated amount from related budget move line
                project.allocated_amount = project.budget_move_line_id.allocated
            else:
                project.allocated_amount = 0.0

    @api.depends("budget_amount", "allocated_amount")
    def _compute_remaining_amount(self):
        for project in self:
            project.remaining_amount = project.budget_amount - project.allocated_amount

    @api.constrains("budget_amount")
    def _check_budget_amount(self):
        for project in self:
            if project.budget_amount < 0:
                raise ValidationError(_("Budget amount cannot be negative."))

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for project in self:
            if project.date_from and project.date_to:
                if project.date_from > project.date_to:
                    raise ValidationError(_("Start date must be before end date."))

    @api.model_create_multi
    def create(self, vals_list):
        """Override to set default analytic values from budget move line if created from there"""
        for vals in vals_list:
            if vals.get("budget_move_line_id"):
                line = self.env["budget.move.line"].browse(vals["budget_move_line_id"])
                # Set default analytic dimensions from budget move line
                if not vals.get("department_analytic_id") and line.department_analytic_id:
                    vals["department_analytic_id"] = line.department_analytic_id.id
                if not vals.get("activity_analytic_id") and line.activity_analytic_id:
                    vals["activity_analytic_id"] = line.activity_analytic_id.id
                if not vals.get("fund_analytic_id") and line.fund_analytic_id:
                    vals["fund_analytic_id"] = line.fund_analytic_id.id
                if not vals.get("source_analytic_id") and line.source_analytic_id:
                    vals["source_analytic_id"] = line.source_analytic_id.id
                # Set budget account from line if not provided
                if not vals.get("budget_account_id") and line.account_id:
                    vals["budget_account_id"] = line.account_id.id
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm the project"""
        self.ensure_one()
        if self.state != "draft":
            raise ValidationError(_("Only draft projects can be confirmed."))
        self.state = "confirmed"

    def action_done(self):
        """Mark project as done"""
        self.ensure_one()
        if self.state != "confirmed":
            raise ValidationError(_("Only confirmed projects can be marked as done."))
        self.state = "done"

    def action_cancel(self):
        """Cancel the project"""
        self.ensure_one()
        if self.state == "done":
            raise ValidationError(_("Cannot cancel a completed project."))
        self.state = "cancel"

    def action_draft(self):
        """Reset to draft"""
        self.ensure_one()
        if self.state != "cancel":
            raise ValidationError(_("Only cancelled projects can be reset to draft."))
        self.state = "draft"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        for project in self:
            if project.state == "done":
                raise ValidationError(_("Cannot delete a completed project."))