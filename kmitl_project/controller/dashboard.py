# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class KmitlProjectDashboard(http.Controller):

    @http.route("/project/dashboard", type="http", auth="public", website=True)
    def dashboard(self, **kw):
        """Main dashboard page with Impact-based statistics"""
        values = self._prepare_dashboard_values(**kw)
        return request.render("kmitl_project.portal_dashboard", values)

    def _prepare_dashboard_values(self, **kw):
        """Prepare all values for the dashboard template"""
        Project = request.env["kmitl.project"].sudo()
        FiscalYear = request.env["account.fiscal.year"].sudo()
        AnalyticAccount = request.env["account.analytic.account"].sudo()

        # Fiscal years - sorted descending (newest first)
        fiscal_years = FiscalYear.search([], order="date_from desc")

        # Default to latest fiscal year if not specified
        fiscal_year_id = kw.get("fiscal_year_id")
        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = str(fiscal_years[0].id)

        # Departments - only root level (parent_id is null)
        departments_plan = request.env.ref(
            "account_analytic_kmitl.analytic_plan_departments"
        )
        departments = AnalyticAccount.search(
            [
                ("root_plan_id", "=", departments_plan.id),
                ("parent_id", "=", False),
            ],
            order="code",
        )

        # Build domain excluding draft and cancel states
        domain = self._build_project_domain(
            fiscal_year_id=fiscal_year_id,
            department_id=kw.get("department_id"),
        )

        # Get all projects matching filters
        projects = Project.search(domain)

        # Calculate impact statistics
        impact_stats = self._calculate_impact_stats(projects)

        # Prepare pie chart data for budget by impact
        chart_data = self._prepare_pie_chart_data(projects)

        return {
            # Filter options
            "fiscal_years": fiscal_years,
            "departments": departments,
            # Current filter values
            "current_fiscal_year_id": fiscal_year_id or "",
            "current_department_id": kw.get("department_id", ""),
            # Projects data
            "projects": projects,
            # Impact statistics
            "impact_stats": impact_stats,
            # Chart data (JSON for JavaScript)
            "chart_data": chart_data,
        }

    def _build_project_domain(self, **kw):
        """Build search domain excluding draft and cancel states"""
        domain = [
            ("active", "=", True),
            ("state", "not in", ["draft", "cancel"]),
        ]

        if kw.get("fiscal_year_id"):
            domain.append(("account_fiscal_year_id", "=", int(kw["fiscal_year_id"])))

        if kw.get("department_id"):
            dept_id = str(kw["department_id"])
            domain.append(("analytic_distribution", "ilike", dept_id))

        return domain

    def _calculate_impact_stats(self, projects):
        """Calculate project counts by impact category"""
        stats = {
            "total": len(projects),
            "education": 0,
            "academic": 0,
            "industrial": 0,
            "social": 0,
        }

        # Get impact references
        impact_refs = {
            "education": request.env.ref(
                "kmitl_project.education", raise_if_not_found=False
            ),
            "academic": request.env.ref(
                "kmitl_project.academic", raise_if_not_found=False
            ),
            "industrial": request.env.ref(
                "kmitl_project.industrial", raise_if_not_found=False
            ),
            "social": request.env.ref(
                "kmitl_project.social", raise_if_not_found=False
            ),
        }

        for key, impact in impact_refs.items():
            if impact:
                stats[key] = len(
                    projects.filtered(lambda p, i=impact: p.impact_id.id == i.id)
                )

        return stats

    def _prepare_pie_chart_data(self, projects):
        """Prepare pie chart data for budget by impact"""
        impact_budgets = {}

        for proj in projects:
            impact_name = proj.impact_id.name if proj.impact_id else "ไม่ระบุ"
            budget = sum(p.amount for p in proj.plan_ids)
            impact_budgets[impact_name] = impact_budgets.get(impact_name, 0) + budget

        # Format for ECharts pie chart
        pie_data = [
            {"name": name, "value": value}
            for name, value in impact_budgets.items()
            if value > 0
        ]

        return json.dumps({"budget_by_impact": pie_data})
