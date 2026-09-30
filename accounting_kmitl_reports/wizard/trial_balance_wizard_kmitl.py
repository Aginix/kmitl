# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class TrialBalanceReportWizardKmitl(models.TransientModel):
    """Non-user-facing carrier model.

    The trial balance is reached through an OWL client action, not a wizard
    form. This model is kept only so the ``ir.actions.report`` records have a
    valid ``model`` to render against; all filters travel through the report
    ``data`` dict. The three fields below just describe the printed record;
    the model name is unchanged from when it inherited the OCA wizard, to
    avoid a model rename migration.
    """

    _name = "trial.balance.report.wizard.kmitl"
    _description = "KMITL Trial Balance Report (PDF carrier)"

    company_id = fields.Many2one(
        comodel_name="res.company", default=lambda self: self.env.company
    )
    date_from = fields.Date()
    date_to = fields.Date()
