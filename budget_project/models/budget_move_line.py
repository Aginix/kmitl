from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BudgetMoveLine(models.Model):
    _inherit = "budget.move.line"

    budget_project_ids = fields.One2many(
        "budget.project",
        "budget_move_line_id",
        string="Projects/Activities",
        domain=[("budget_move_line_id.is_virtual_line", "=", False)],
    )
    project_enabled = fields.Boolean(
        string="Project Enabled",
        related="account_id.project_enabled",
        readonly=True,
        store=True,
    )
    total_project_amount = fields.Float(
        string="Total Project Amount",
        compute="_compute_project_amounts",
        store=True,
        digits="Budget",
    )
    unallocated_project_amount = fields.Float(
        string="Unallocated Project Amount",
        compute="_compute_project_amounts",
        store=True,
        digits="Budget",
    )

    @api.depends("budget_project_ids", "budget_project_ids.budget_amount", "balance")
    def _compute_project_amounts(self):
        for line in self:
            total = sum(line.budget_project_ids.mapped("budget_amount"))
            line.total_project_amount = total
            line.unallocated_project_amount = line.balance - total

    @api.constrains("budget_project_ids", "balance")
    def _check_project_amounts(self):
        for line in self:
            if line.project_enabled and line.unallocated_project_amount < 0:
                raise ValidationError(
                    _("Total project amounts cannot exceed the allocated budget amount.")
                )

    def _prepare_virtual_line_vals(self, original_vals, move, source_line_id=None):
        vals = super()._prepare_virtual_line_vals(original_vals, move, source_line_id=source_line_id)
        if "budget_project_ids" in vals:
            del vals["budget_project_ids"]
        return vals
