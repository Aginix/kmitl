from odoo import api, fields, models


class KrisProject(models.Model):
    _inherit = "kris.project"

    extra_analytic_ids = fields.One2many(
        "kris.project.extra.analytic.line",
        "project_id",
        string="Extra Payees",
        tracking=True,
    )

    extra_value = fields.Monetary(
        compute="_compute_extra_value",
        store=True,
        readonly=True,
        tracking=True,
    )

    extra_value_project_pct = fields.Float(
        string="As % of Project Value",
        compute="_compute_extra_value_project_pct",
        store=True,
        digits=(16, 4),
        readonly=True,
    )

    @api.depends("extra_analytic_ids.amount")
    def _compute_extra_value(self):
        for project in self:
            project.extra_value = sum(project.extra_analytic_ids.mapped("amount"))

    @api.depends("extra_value", "project_value")
    def _compute_extra_value_project_pct(self):
        for project in self:
            base = project.project_value
            project.extra_value_project_pct = (project.extra_value / base) if base else 0.0
