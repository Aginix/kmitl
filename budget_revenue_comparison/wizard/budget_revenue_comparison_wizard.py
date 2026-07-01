# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class BudgetRevenueComparisonWizard(models.TransientModel):
    """Throwaway carrier so ``ir.actions.report`` (XLSX) has a record to render
    against. Not user-facing: the OWL client action builds it on export and the
    real filters travel in the report ``data`` dict, not on this record."""

    _name = "budget.revenue.comparison.wizard"
    _description = "Budget Revenue Comparison Report Carrier"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year", string="Fiscal Year"
    )
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
