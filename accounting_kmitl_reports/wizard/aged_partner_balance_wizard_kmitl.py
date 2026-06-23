# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AgedPartnerReportWizardKmitl(models.TransientModel):
    """Non-user-facing carrier model.

    The aged partner balance is reached through an OWL client action, not a
    wizard form. This model exists only so the ``ir.actions.report`` has a
    valid ``model`` to render against; all filters travel through the report
    ``data`` dict.
    """

    _name = "aged.partner.report.wizard.kmitl"
    _description = "KMITL Aged Partner Balance Report (PDF carrier)"

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )
    date_at = fields.Date()
