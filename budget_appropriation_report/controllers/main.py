# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class BudgetAppropriationReportController(http.Controller):

    @http.route(
        ["/budget_appropriation_report/<int:report_id>/<string:report_type>"],
        type="http",
        auth="user",
        website=True,
    )
    def budget_appropriation_report(self, report_id, report_type, **kw):
        """Render budget appropriation report in HTML or PDF format."""
        report_record = request.env["budget.appropriation.report"].browse(report_id)
        if not report_record.exists():
            return request.redirect("/web")

        if report_type == "html":
            report = request.env.ref(
                "budget_appropriation_report.action_report_budget_appropriation_report"
            )
            html = request.env["ir.actions.report"]._render_qweb_html(
                report.id, [report_record.id]
            )[0]
            return request.make_response(
                html,
                headers=[
                    ("Content-Type", "text/html"),
                    ("Content-Length", len(html)),
                ],
            )
        elif report_type == "pdf":
            report = request.env.ref(
                "budget_appropriation_report.action_report_budget_appropriation_report"
            )
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [report_record.id]
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="Budget Appropriation Report - {report_record.name}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)

        return request.redirect("/web")
