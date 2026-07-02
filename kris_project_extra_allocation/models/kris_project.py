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

    @api.depends("extra_analytic_ids.amount")
    def _compute_extra_value(self):
        for project in self:
            project.extra_value = sum(project.extra_analytic_ids.mapped("amount"))
