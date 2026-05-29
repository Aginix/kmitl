# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class TrialBalanceReportWizardKmitl(models.TransientModel):
    _name = "trial.balance.report.wizard.kmitl"
    _inherit = "trial.balance.report.wizard"
    _description = "KMITL Trial Balance Report Wizard"

    def _build_report_data(self):
        self.ensure_one()
        return {
            "wizard_name": self._name,
            "wizard_id": self.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "only_posted_moves": self.target_move == "posted",
            "hide_account_at_0": self.hide_account_at_0,
            "foreign_currency": self.foreign_currency,
            "company_id": self.company_id.id,
            "account_ids": self.account_ids.ids or [],
            "partner_ids": self.partner_ids.ids or [],
            "journal_ids": self.journal_ids.ids or [],
            "fy_start_date": self.fy_start_date,
            "show_hierarchy": self.show_hierarchy,
            "limit_hierarchy_level": self.limit_hierarchy_level,
            "show_hierarchy_level": self.show_hierarchy_level,
            "hide_parent_hierarchy_level": self.hide_parent_hierarchy_level,
            "show_partner_details": self.show_partner_details,
            "unaffected_earnings_account": self.unaffected_earnings_account.id,
            "account_financial_report_lang": self.env.lang,
            "grouped_by": self.grouped_by,
        }

    def _print_report(self, report_type):
        self.ensure_one()
        data = self._build_report_data()
        if report_type == "qweb-html":
            xmlid = "accounting_kmitl_reports.action_report_trial_balance_kmitl_html"
        else:
            xmlid = "accounting_kmitl_reports.action_report_trial_balance_kmitl"
        report = self.env.ref(xmlid)
        return report.report_action(self, data=data)
