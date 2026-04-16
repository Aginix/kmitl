from odoo import api, models


class ReportCompilationF5Pdf(models.AbstractModel):
    _name = "report.budget_appropriation_summary.report_compilation_f5"
    _description = "Compilation F5 PDF Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            docids = self.env.context.get("active_ids", [])
        show_note = data.get("show_note", True) if isinstance(data, dict) else True
        show_itemized = (
            data.get("show_itemized", False) if isinstance(data, dict) else False
        )
        return {
            "doc_ids": docids,
            "doc_model": "budget.appropriation.compilation",
            "docs": self.env["budget.appropriation.compilation"].browse(docids),
            "show_note": show_note,
            "show_itemized": show_itemized,
        }
