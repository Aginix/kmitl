# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class BudgetAppropriationDashboardController(http.Controller):

    @http.route(
        "/budget_appropriation/dashboard/data",
        type="json",
        auth="user",
    )
    def get_dashboard_data(self, fiscal_year_id=None, source_id=None, **kw):
        """Get dashboard data for budget appropriation."""
        # Get fiscal years for filter options
        fiscal_years = request.env["account.fiscal.year"].search(
            [], order="date_from desc"
        )
        fiscal_year_options = [
            {"id": fy.id, "name": fy.name} for fy in fiscal_years
        ]

        # Get sources for filter options
        sources = request.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "sources")], order="code"
        )
        source_options = [
            {"id": src.id, "name": src.name, "code": src.code} for src in sources
        ]

        # Determine selected fiscal year
        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = fiscal_years[0].id

        fiscal_year = None
        if fiscal_year_id:
            fy = request.env["account.fiscal.year"].browse(fiscal_year_id)
            if fy.exists():
                fiscal_year = {"id": fy.id, "name": fy.name}

        # Get dashboard statistics from budget.appropriation.report
        stats = self._get_dashboard_stats(fiscal_year_id, source_id)

        return {
            "filter_options": {
                "fiscal_years": fiscal_year_options,
                "sources": source_options,
            },
            "filters": {
                "fiscal_year_id": fiscal_year_id,
                "source_id": source_id,
            },
            "fiscal_year": fiscal_year,
            "stats": stats,
        }

    def _get_dashboard_stats(self, fiscal_year_id, source_id):
        """Calculate dashboard statistics from budget.appropriation.report."""
        domain = []
        if fiscal_year_id:
            domain.append(("account_fiscal_year_id", "=", fiscal_year_id))
        if source_id:
            domain.append(("source_analytic_id", "=", source_id))

        reports = request.env["budget.appropriation.report"].search(domain)

        # Collect all appropriations from reports
        all_revenue_appropriations = reports.mapped("revenue_appropriation_ids")
        all_expense_appropriations = reports.mapped("expense_appropriation_ids")

        # Calculate totals
        total_revenue = sum(all_revenue_appropriations.mapped("amount_total"))
        total_expense = sum(all_expense_appropriations.mapped("amount_total"))

        # Count distinct departments
        revenue_departments = all_revenue_appropriations.mapped(
            "department_analytic_id"
        )
        expense_departments = all_expense_appropriations.mapped(
            "department_analytic_id"
        )
        all_departments = revenue_departments | expense_departments
        department_count = len(all_departments)

        # Group expense by department for treemap
        department_expenses = {}
        for approp in all_expense_appropriations:
            dept = approp.department_analytic_id
            if dept:
                key = dept.id
                if key not in department_expenses:
                    department_expenses[key] = {
                        "name": dept.name,
                        "value": 0,
                    }
                department_expenses[key]["value"] += approp.amount_total

        # Sort by value descending
        treemap_data = sorted(
            department_expenses.values(), key=lambda x: x["value"], reverse=True
        )

        return {
            "report_count": len(reports),
            "department_count": department_count,
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "pie_chart": [
                {"name": "รายรับ", "value": total_revenue},
                {"name": "รายจ่าย", "value": total_expense},
            ],
            "treemap_data": treemap_data,
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
