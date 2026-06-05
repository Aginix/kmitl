# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class TrialBalanceReportWizardKmitl(models.TransientModel):
    """Non-user-facing carrier model.

    The trial balance is now reached through an OWL client action, not a
    wizard form. This model is kept only so the ``ir.actions.report`` has a
    valid ``model`` to render against; all filters travel through the report
    ``data`` dict. It inherits the OCA wizard purely to avoid a model rename
    migration.
    """

    _name = "trial.balance.report.wizard.kmitl"
    _inherit = "trial.balance.report.wizard"
    _description = "KMITL Trial Balance Report (PDF carrier)"
