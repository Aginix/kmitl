from odoo import api, models


class BudgetAppropriationF5ReportPdf(models.AbstractModel):
    _name = "report.budget_appropriation.report_budget_appropriation_f5"
    _description = "Budget Appropriation F5 PDF Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            docids = self.env.context.get("active_ids", [])
        show_note = data.get("show_note", True) if isinstance(data, dict) else True
        return {
            "doc_ids": docids,
            "doc_model": "budget.appropriation",
            "docs": self.env["budget.appropriation"].browse(docids),
            "show_note": show_note,
        }
