# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# States whose budget_amount must not be counted in the dashboard: the project
# either has not reserved anything yet (draft, to_verify) or has released what it
# reserved (rejected, cancel). Everything from to_send onward holds a live
# reservation and belongs in the totals (kmitl_project ADR-0005).
UNBUDGETED_STATES = ["draft", "to_verify", "rejected", "cancel"]


class KmitlProjectDashboard(http.Controller):
    """Project dashboard grouped by the *department* financial dimension
    (``department_analytic_id``, the ``departments`` analytic plan). Department
    ids handled here are ``account.analytic.account`` ids."""

    def _departments(self):
        """Root-level department-dimension accounts (the dashboard's group axis)."""
        return (
            request.env["account.analytic.account"]
            .sudo()
            .search(
                [
                    ("root_plan_id.code", "=", "departments"),
                    ("parent_id", "=", False),
                ],
                order="code",
            )
        )

    @http.route("/project/dashboard", type="http", auth="public", website=True)
    def dashboard(self, **kw):
        """Main dashboard page - renders template with filter options"""
        values = self._prepare_filter_options(**kw)
        return request.render("kmitl_project.portal_dashboard", values)

    @http.route("/project/dashboard/api", type="json", auth="public", csrf=False)
    def dashboard_api(self, fiscal_year_id=None, department_id=None, **kw):
        """API endpoint for dashboard data"""
        data = self._prepare_dashboard_data(
            fiscal_year_id=fiscal_year_id,
            department_id=department_id,
        )
        return data

    @http.route(
        "/project/dashboard/<int:department_id>",
        type="http",
        auth="public",
        website=True,
    )
    def department_dashboard(self, department_id, **kw):
        """Department-specific dashboard page (department_id is an analytic account id)"""
        Department = request.env["account.analytic.account"].sudo()
        department = Department.browse(department_id)

        if not department.exists():
            return request.redirect("/project/dashboard")

        values = self._prepare_department_filter_options(department, **kw)
        return request.render("kmitl_project.portal_department_dashboard", values)

    @http.route(
        "/project/dashboard/<int:department_id>/api",
        type="json",
        auth="public",
        csrf=False,
    )
    def department_dashboard_api(self, department_id, fiscal_year_id=None, **kw):
        """API endpoint for department dashboard data"""
        data = self._prepare_department_dashboard_data(
            department_id=department_id,
            fiscal_year_id=fiscal_year_id,
        )
        return data

    def _prepare_filter_options(self, **kw):
        """Prepare filter options for the dashboard template (JSON for OWL)"""
        FiscalYear = request.env["account.fiscal.year"].sudo()

        # Fiscal years - sorted descending (newest first)
        fiscal_years = FiscalYear.search([], order="date_from desc")

        # Default to latest fiscal year if not specified
        fiscal_year_id = kw.get("fiscal_year_id")
        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = str(fiscal_years[0].id)

        # Departments - root-level accounts of the departments dimension
        departments = self._departments()

        # Convert to JSON for OWL component
        fiscal_years_json = json.dumps([
            {"id": fy.id, "name": fy.name}
            for fy in fiscal_years
        ])
        departments_json = json.dumps([
            {"id": dept.id, "code": dept.code or "", "name": dept.name}
            for dept in departments
        ])

        return {
            "fiscal_years_json": fiscal_years_json,
            "departments_json": departments_json,
            "current_fiscal_year_id": fiscal_year_id or "",
            "current_department_id": kw.get("department_id", ""),
        }

    def _prepare_dashboard_data(self, fiscal_year_id=None, department_id=None):
        """Prepare all dashboard data for API response"""
        Project = request.env["kmitl.project"].sudo()

        # Departments - root-level accounts of the departments dimension
        departments = self._departments()

        # Build domain excluding draft and cancel states
        domain = self._build_project_domain(
            fiscal_year_id=fiscal_year_id,
            department_id=department_id,
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
            "impact_stats": impact_stats,
            "chart_data": chart_data,
            "department_budget_table": department_budget_table,
        }

    def _build_project_domain(self, **kw):
        """Build search domain excluding the states that hold no reserved budget"""
        domain = [
            ("active", "=", True),
            ("state", "not in", UNBUDGETED_STATES),
        ]

        if kw.get("fiscal_year_id"):
            domain.append(("account_fiscal_year_id", "=", int(kw["fiscal_year_id"])))

        if kw.get("department_id"):
            # Use parent_path to include all child departments of the dimension
            Department = request.env["account.analytic.account"].sudo()
            dept = Department.browse(int(kw["department_id"]))
            if dept.exists() and dept.parent_path:
                child_depts = Department.search([
                    ("parent_path", "=like", dept.parent_path + "%"),
                    ("root_plan_id.code", "=", "departments"),
                ])
                domain.append(("department_analytic_id", "in", child_depts.ids))
            else:
                domain.append(("department_analytic_id", "=", int(kw["department_id"])))
                domain.append(
                    ("department_analytic_id.root_plan_id.code", "=", "departments")
                )

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

        return {"budget_by_impact": pie_data}

    def _prepare_department_budget_table(self, departments, projects):
        """Prepare department budget table data (departments dimension)"""
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
            # Get projects for this department and all child departments (using parent_path)
            dept_projects = projects.filtered(
                lambda p, d=dept: (
                    p.department_analytic_id and
                    p.department_analytic_id.parent_path and
                    d.parent_path and
                    p.department_analytic_id.parent_path.startswith(d.parent_path)
                )
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
                "department_id": dept.id,
                "department_code": dept.code or "",
                "department_name": dept.name,
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

    def _prepare_department_filter_options(self, department, **kw):
        """Prepare filter options for department dashboard (departments dimension)"""
        FiscalYear = request.env["account.fiscal.year"].sudo()

        # Fiscal years - sorted descending (newest first)
        fiscal_years = FiscalYear.search([], order="date_from desc")

        # Default to latest fiscal year if not specified
        fiscal_year_id = kw.get("fiscal_year_id")
        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = str(fiscal_years[0].id)

        fiscal_years_json = json.dumps([
            {"id": fy.id, "name": fy.name}
            for fy in fiscal_years
        ])

        return {
            "department_id": department.id,
            "department_name": department.name,
            "department_code": department.code or "",
            "fiscal_years_json": fiscal_years_json,
            "current_fiscal_year_id": fiscal_year_id or "",
        }

    def _prepare_department_dashboard_data(self, department_id, fiscal_year_id=None):
        """Prepare department dashboard data for API response (departments dimension)"""
        Project = request.env["kmitl.project"].sudo()
        Department = request.env["account.analytic.account"].sudo()

        department = Department.browse(department_id)
        if not department.exists():
            return {"error": "Department not found"}

        # Build domain for this department (departments dimension)
        domain = self._build_project_domain_for_department(
            fiscal_year_id=fiscal_year_id,
            department_id=department_id,
        )

        projects = Project.search(domain)

        # Calculate impact statistics
        impact_stats = self._calculate_impact_stats(projects)

        # Prepare project list table
        projects_table = self._prepare_projects_table(projects)

        return {
            "impact_stats": impact_stats,
            "projects_table": projects_table,
        }

    def _build_project_domain_for_department(self, fiscal_year_id=None, department_id=None):
        """Build search domain for department-dimension filtering using parent_path"""
        domain = [
            ("active", "=", True),
            ("state", "not in", UNBUDGETED_STATES),
        ]

        if fiscal_year_id:
            domain.append(("account_fiscal_year_id", "=", int(fiscal_year_id)))

        if department_id:
            # Use parent_path to include all child departments of the dimension
            Department = request.env["account.analytic.account"].sudo()
            dept = Department.browse(int(department_id))
            if dept.exists() and dept.parent_path:
                child_depts = Department.search([
                    ("parent_path", "=like", dept.parent_path + "%"),
                    ("root_plan_id.code", "=", "departments"),
                ])
                domain.append(("department_analytic_id", "in", child_depts.ids))
            else:
                domain.append(("department_analytic_id", "=", int(department_id)))
                domain.append(
                    ("department_analytic_id.root_plan_id.code", "=", "departments")
                )

        return domain

    def _prepare_projects_table(self, projects):
        """Prepare project list table data for department dashboard"""
        source_1 = request.env.ref(
            "account_analytic_kmitl.source_1", raise_if_not_found=False
        )
        source_2 = request.env.ref(
            "account_analytic_kmitl.source_2", raise_if_not_found=False
        )

        source_1_id = source_1.id if source_1 else None
        source_2_id = source_2.id if source_2 else None

        table_data = []

        for proj in projects:
            budget = proj.budget_amount or 0
            source_id = self._get_source_id_from_distribution(proj)

            budget_source_1 = budget if source_id == source_1_id else 0
            budget_source_2 = budget if source_id == source_2_id else 0
            budget_other = budget if source_id not in [source_1_id, source_2_id] else 0

            # Collect strategic alignment badges
            badges = []
            if proj.impact_id:
                badges.append({
                    "text": proj.impact_id.name,
                    "color": "info",
                })
            if proj.global_index_id:
                badges.append({
                    "text": proj.global_index_id.name,
                    "color": "primary",
                })
            if proj.fight_id:
                badges.append({
                    "text": proj.fight_id.name,
                    "color": "secondary",
                })

            table_data.append({
                "id": proj.id,
                "name": proj.name,
                "budget_source_1": budget_source_1,
                "budget_source_2": budget_source_2,
                "budget_other": budget_other,
                "q1": "-",
                "q2": "-",
                "q3": "-",
                "q4": "-",
                "total_actual": "-",
                "state": proj.state,
                "state_display": dict(proj._fields["state"].selection).get(
                    proj.state, proj.state
                ),
                "badges": badges,
                "write_date": proj.write_date.strftime("%d/%m/%Y %H:%M")
                if proj.write_date
                else "-",
            })

        return table_data
