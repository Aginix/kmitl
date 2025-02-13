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
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
    )

    @api.depends("analytic_distribution")
    def _compute_analytic_distribution(self):
        for record in self:
            # Reset fields in case distribution keys are missing or change
            record.activity_analytic_id = False
            record.department_analytic_id = False
            record.fund_analytic_id = False
            record.source_analytic_id = False

            # Extract the JSON data from 'analytic_distribution'
            distribution = record.analytic_distribution or {}

            _logger.info(distribution)

            # Iterate over the JSON data to find and assign analytic accounts
            for analytic_id_str, _percent in distribution.items():
                # Convert the string ID to integer
                analytic_id = int(analytic_id_str)
                analytic_account = self.env["account.analytic.account"].browse(
                    analytic_id
                )

                _logger.info(analytic_id)

                # Check analytic plan or dimension type to assign to correct field
                if analytic_account.plan_id.name == "แผนงาน/กิจกรรม":
                    record.activity_analytic_id = analytic_account
                elif analytic_account.plan_id.name == "ส่วนงาน":
                    record.department_analytic_id = analytic_account
                elif analytic_account.plan_id.name == "กองทุน":
                    record.fund_analytic_id = analytic_account
                elif analytic_account.plan_id.name == "แหล่งเงิน":
                    record.source_analytic_id = analytic_account
