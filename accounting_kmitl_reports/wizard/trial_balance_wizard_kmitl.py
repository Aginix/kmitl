# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class TrialBalanceReportWizardKmitl(models.TransientModel):
    _name = "trial.balance.report.wizard.kmitl"
    _inherit = "trial.balance.report.wizard"
    _description = "KMITL Trial Balance Report Wizard"

    def _print_report(self, report_type):
        self.ensure_one()
        data = self._prepare_report_data()
        report = self.env.ref(
            "accounting_kmitl_reports.action_report_trial_balance_kmitl"
        )
        return report.report_action(self, data=data)
