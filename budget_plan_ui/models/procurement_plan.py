import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    budget_plan_line_id = fields.Many2one(
        "budget.appropriation.line",
        string="Budget Plan line",
        ondelete="cascade",
    )
    hide_header = fields.Boolean(compute="_compute_hide_header", store=False)

    @api.depends_context("hide_header")
    def _compute_hide_header(self):
        for rec in self:
            rec.hide_header = self.env.context.get("hide_header", False)
