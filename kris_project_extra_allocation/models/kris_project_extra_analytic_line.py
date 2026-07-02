from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class KrisProjectExtraAnalyticLine(models.Model):
    _name = "kris.project.extra.analytic.line"
    _description = "KRIS Project Extra Payee Line"
    _order = "id"

    project_id = fields.Many2one(
        "kris.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Extra Payee",
        domain=[("root_plan_id.code", "=", "departments")],
        required=True,
    )
    amount = fields.Monetary(
        string="Amount",
    )
    percentage = fields.Float(
        string="Percentage",
        digits=(5, 2),
        compute="_compute_percentage",
        store=True,
    )
    currency_id = fields.Many2one(
        related="project_id.currency_id",
        store=True,
    )

    _sql_constraints = [
        (
            "unique_project_analytic",
            "UNIQUE(project_id, analytic_account_id)",
            "Each payee can only appear once per project.",
        ),
    ]

    @api.depends("amount", "project_id.extra_analytic_ids.amount")
    def _compute_percentage(self):
        for line in self:
            total = sum(line.project_id.extra_analytic_ids.mapped("amount"))
            line.percentage = (line.amount / total * 100.0) if total else 0.0

    @api.constrains("project_id", "analytic_account_id")
    def _check_unique_analytic_per_project(self):
        for line in self:
            dup = self.search(
                [
                    ("project_id", "=", line.project_id.id),
                    ("analytic_account_id", "=", line.analytic_account_id.id),
                    ("id", "!=", line.id),
                ],
                limit=1,
            )
            if dup:
                raise ValidationError(
                    _("Payee %s is already added to this project.")
                    % line.analytic_account_id.display_name
                )
