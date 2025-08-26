import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AnalyticDistributionMixin(models.AbstractModel):
    _name = "analytic.distribution.mixin"
    _inherit = ["analytic.mixin"]
    _description = "Analytic Distribution Mixin"

    # Define the Many2one fields for each analytic dimension
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "activities")],
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "departments")],
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "funds")],
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "sources")],
    )

    @api.depends(lambda self: self._analytic_fields())
    def _compute_analytic_distribution(self):
        for record in self:
            distribution = {}

            # Add each dimension to distribution with 100% allocation
            for field_name in self._analytic_fields():
                analytic_account = getattr(record, field_name)
                if analytic_account:
                    distribution[str(analytic_account.id)] = 100.0

            record.analytic_distribution = distribution if distribution else False

    def _analytic_fields(self):
        return ["department_analytic_id", "activity_analytic_id", "fund_analytic_id", "source_analytic_id"]

    @api.onchange(lambda self: self._analytic_fields())
    def _onchange_analytic_fields(self):
        """Update analytic distribution when individual fields change"""
        if self.activity_analytic_id or self.fund_analytic_id or self.department_analytic_id or self.source_analytic_id:
            distribution = {}

            # Add each dimension to distribution with 100% allocation
            for field_name in self._analytic_fields():
                analytic_account = getattr(self, field_name)
                if analytic_account:
                    distribution[str(analytic_account.id)] = 100.0

            self.analytic_distribution = distribution if distribution else False
