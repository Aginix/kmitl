# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class BudgetAppropriationDashboardController(http.Controller):

    @http.route(
        "/budget_appropriation/dashboard/data",
        type="json",
        auth="user",
    )
    def get_dashboard_data(self, fiscal_year_id=None, **kw):
        """Get dashboard data for budget appropriation."""
        # Get fiscal years for filter options
        fiscal_years = (
            request.env["account.fiscal.year"]
            .search([], order="date_from desc")
        )
        fiscal_year_options = [
            {"id": fy.id, "name": fy.name} for fy in fiscal_years
        ]

        # Determine selected fiscal year
        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = fiscal_years[0].id

        fiscal_year = None
        if fiscal_year_id:
            fy = request.env["account.fiscal.year"].browse(fiscal_year_id)
            if fy.exists():
                fiscal_year = {"id": fy.id, "name": fy.name}

        return {
            "filter_options": {
                "fiscal_years": fiscal_year_options,
            },
            "filters": {
                "fiscal_year_id": fiscal_year_id,
            },
            "fiscal_year": fiscal_year,
            "data": {},
        }


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
