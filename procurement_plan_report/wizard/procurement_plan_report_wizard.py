# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class ProcurementPlanReportWizard(models.TransientModel):
    """Throwaway carrier so ``ir.actions.report`` (XLSX) has a record to render
    against. Not user-facing: the OWL client action builds it on export and the
    real filters travel in the report ``data`` dict, not on this record."""

    _name = "procurement.plan.report.wizard"
    _description = "Procurement Plan Report Carrier"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    report_type = fields.Selection(
        [
            ("construction", "สิ่งก่อสร้าง"),
            ("equipment", "ครุภัณฑ์ (งวดเดียว)"),
            ("equipment_multi", "ครุภัณฑ์ (หลายงวด)"),
        ],
        string="Report Type",
        default="construction",
    )
    fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year", string="Fiscal Year"
    )
