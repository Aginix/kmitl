from odoo import http
from odoo.http import request


class BudgetAppropriationSummaryController(http.Controller):

    @http.route(
        ["/budget_appropriation_summary/<int:summary_id>/<string:report_type>"],
        type="http",
        auth="user",
        website=True,
    )
    def budget_appropriation_summary_report(self, summary_id, report_type, **kw):
        """Render budget appropriation master summary report in HTML or PDF format."""
        record = request.env["budget.appropriation.master.summary"].browse(summary_id)
        if not record.exists():
            return request.redirect("/web")

        report = request.env.ref(
            "budget_appropriation_summary.action_report_master_summary"
        )

        if report_type == "html":
            html = request.env["ir.actions.report"]._render_qweb_html(
                report.id, [record.id]
            )[0]
            return request.make_response(
                html,
                headers=[
                    ("Content-Type", "text/html"),
                    ("Content-Length", len(html)),
                ],
            )
        elif report_type == "pdf":
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [record.id]
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="{record.name}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)

        return request.redirect("/web")
