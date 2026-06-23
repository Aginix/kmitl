# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class GeneralLedgerReportWizardKmitl(models.TransientModel):
    """Non-user-facing carrier model.

    The general ledger is reached through an OWL client action, not a wizard
    form. This model is kept only so the ``ir.actions.report`` has a valid
    ``model`` to render against; all filters travel through the report ``data``
    dict. It inherits the OCA wizard purely to reuse its fields.
    """

    _name = "general.ledger.report.wizard.kmitl"
    _inherit = "general.ledger.report.wizard"
    _description = "KMITL General Ledger Report (PDF carrier)"
