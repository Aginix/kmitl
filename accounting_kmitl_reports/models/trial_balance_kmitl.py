# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class TrialBalanceReportKmitl(models.AbstractModel):
    _name = "report.accounting_kmitl_reports.trial_balance_kmitl"
    _description = "KMITL Trial Balance Report"
    _inherit = "report.account_financial_report.trial_balance"

    @staticmethod
    def _format_amount(value):
        if not value:
            return ""
        return f"{value:,.2f}"

    def _get_report_values(self, docids, data):
        res = super()._get_report_values(docids, data)
        wizard_id = data.get("wizard_id")
        company = self.env["res.company"].browse(data["company_id"])
        thai_helper = self.env["thai.date.mixin"]
        rows = []
        total_debit = 0.0
        total_credit = 0.0
        for account in res.get("trial_balance") or []:
            opening = account.get("initial_balance") or 0.0
            ending = account.get("ending_balance") or 0.0
            debit = account.get("debit") or 0.0
            credit = account.get("credit") or 0.0
            opening_debit = opening if opening >= 0 else 0.0
            opening_credit = -opening if opening < 0 else 0.0
            ending_debit = ending if ending >= 0 else 0.0
            ending_credit = -ending if ending < 0 else 0.0
            rows.append({
                "code": account.get("code") or "",
                "name": account.get("name") or "",
                "opening_debit": self._format_amount(opening_debit),
                "opening_credit": self._format_amount(opening_credit),
                "debit": self._format_amount(debit),
                "credit": self._format_amount(credit),
                "ending_debit": self._format_amount(ending_debit),
                "ending_credit": self._format_amount(ending_credit),
            })
            total_debit += debit
            total_credit += credit
        res.update({
            "doc_model": "trial.balance.report.wizard.kmitl",
            "docs": self.env["trial.balance.report.wizard.kmitl"].browse(wizard_id),
            "res_company": company,
            "kmitl_rows": rows,
            "kmitl_total_debit": f"{total_debit:,.2f}",
            "kmitl_total_credit": f"{total_credit:,.2f}",
            "kmitl_zero": "0.00",
            "kmitl_date_from_th": thai_helper.format_date_thai_short(data["date_from"]),
            "kmitl_date_to_th": thai_helper.format_date_thai_short(data["date_to"]),
        })
        return res
