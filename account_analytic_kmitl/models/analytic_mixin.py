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

    analytic_distribution = fields.Json(
        "Analytic",
        inverse="_inverse_analytic_distribution",
        store=True,
        copy=True,
        readonly=False,
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

    def _process_analytic_distribution(self):
        distribution = {}

        for field_name in self._analytic_fields():
            analytic_account = getattr(self, field_name)
            if analytic_account:
                distribution[str(analytic_account.id)] = 100.0

        self.analytic_distribution = distribution if distribution else False

    def _analytic_fields(self):
        return list(self._analytic_keys().values())

    def write(self, vals):
        res = super().write(vals)
        return res

    def _inverse_analytic_distribution(self):
        """When set analytic_distribution set analytic ids"""
        for rec in self.filtered("analytic_distribution"):
            rec._process_analytic_distribution_ids()

    def _analytic_keys(self):
        return {
            "activities": "activity_analytic_id",
            "departments": "department_analytic_id",
            "funds": "fund_analytic_id",
            "sources": "source_analytic_id",
        }

    def _process_analytic_distribution_ids(self):
        keys = self._analytic_keys()
        data = {}
        for account_analytic_id in self.analytic_distribution.keys():
            aa = self.env["account.analytic.account"].browse(int(account_analytic_id))
            if aa and keys.get(aa.plan_id.code, False):
                data[keys.get(aa.plan_id.code)] = aa.id
        if data:
            self.write(data)
