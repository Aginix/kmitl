# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class CashFlowReportWizardKmitl(models.TransientModel):
    """Non-user-facing carrier model.

    The cash flow statement is reached through an OWL client action, not a
    wizard form. This model is kept only so the ``ir.actions.report`` has a
    valid ``model`` to render against; all filters travel through the report
    ``data`` dict.
    """

    _name = "cash.flow.report.wizard.kmitl"
    _description = "KMITL Cash Flow Statement Report (PDF carrier)"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date()
    date_to = fields.Date()
