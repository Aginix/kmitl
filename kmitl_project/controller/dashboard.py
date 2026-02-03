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

        # Prepare department budget table (uses fiscal year filter only)
        dept_domain = self._build_project_domain(fiscal_year_id=fiscal_year_id)
        all_fiscal_projects = Project.search(dept_domain)
        department_budget_table = self._prepare_department_budget_table(
            departments, all_fiscal_projects
        )

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
            # Department budget table
            "department_budget_table": department_budget_table,
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
            budget = proj.budget_amount or 0
            impact_budgets[impact_name] = impact_budgets.get(impact_name, 0) + budget

        # Format for ECharts pie chart
        pie_data = [
            {"name": name, "value": value}
            for name, value in impact_budgets.items()
            if value > 0
        ]

        return json.dumps({"budget_by_impact": pie_data})

    def _prepare_department_budget_table(self, departments, projects):
        """Prepare department budget table data"""
        # Get source references
        source_1 = request.env.ref(
            "account_analytic_kmitl.source_1", raise_if_not_found=False
        )  # เงินแผ่นดิน
        source_2 = request.env.ref(
            "account_analytic_kmitl.source_2", raise_if_not_found=False
        )  # เงินรายได้

        source_1_id = source_1.id if source_1 else None
        source_2_id = source_2.id if source_2 else None

        table_data = []

        for dept in departments:
            # Get projects for this department (match by analytic_distribution)
            dept_projects = projects.filtered(
                lambda p, d=dept: self._project_matches_department(p, d)
            )

            # Calculate budget by source
            budget_source_1 = 0.0  # เงินแผ่นดิน
            budget_source_2 = 0.0  # เงินรายได้
            budget_other = 0.0  # อื่น ๆ

            for proj in dept_projects:
                budget = proj.budget_amount or 0
                source_id = self._get_source_id_from_distribution(proj)

                if source_id == source_1_id:
                    budget_source_1 += budget
                elif source_id == source_2_id:
                    budget_source_2 += budget
                else:
                    budget_other += budget

            total_budget = budget_source_1 + budget_source_2 + budget_other

            table_data.append({
                "department": dept,
                "budget_source_1": budget_source_1,
                "budget_source_2": budget_source_2,
                "budget_other": budget_other,
                "q1": "-",
                "q2": "-",
                "q3": "-",
                "q4": "-",
                "total_budget": total_budget,
            })

        return table_data

    def _project_matches_department(self, project, department):
        """Check if project belongs to department via analytic_distribution"""
        if not project.analytic_distribution:
            return False
        return str(department.id) in str(project.analytic_distribution)

    def _get_source_id_from_distribution(self, project):
        """Extract source analytic ID from project's analytic_distribution"""
        if not project.analytic_distribution:
            return None

        # Get source plan
        sources_plan = request.env.ref(
            "account_analytic_kmitl.analytic_plan_sources", raise_if_not_found=False
        )
        if not sources_plan:
            return None

        # Find source in distribution
        for key in project.analytic_distribution.keys():
            try:
                analytic_id = int(key)
                analytic = request.env["account.analytic.account"].sudo().browse(analytic_id)
                if analytic.exists() and analytic.root_plan_id.id == sources_plan.id:
                    return analytic_id
            except (ValueError, TypeError):
                continue

        return None
