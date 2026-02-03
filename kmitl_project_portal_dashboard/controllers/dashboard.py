import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class KmitlProjectDashboard(http.Controller):

    @http.route("/project/dashboard", type="http", auth="public", website=True)
    def dashboard(self, **kw):
        """Main dashboard page - renders QWeb template with initial data"""
        values = self._prepare_dashboard_values(**kw)
        return request.render(
            "kmitl_project_portal_dashboard.portal_dashboard", values
        )

    def _prepare_dashboard_values(self, **kw):
        """Prepare all values for the dashboard template"""
        Project = request.env["kmitl.project"].sudo()
        FiscalYear = request.env["account.fiscal.year"].sudo()
        AnalyticAccount = request.env["account.analytic.account"].sudo()

        # Get filter options
        fiscal_years = FiscalYear.search([], order="date_from desc")

        # Get 4D dimension options
        activities_plan = request.env.ref(
            "account_analytic_kmitl.analytic_plan_activities"
        )
        activities = AnalyticAccount.search(
            [("root_plan_id", "=", activities_plan.id)], order="code"
        )

        departments_plan = request.env.ref(
            "account_analytic_kmitl.analytic_plan_departments"
        )
        departments = AnalyticAccount.search(
            [("root_plan_id", "=", departments_plan.id)], order="code"
        )

        funds_plan = request.env.ref("account_analytic_kmitl.analytic_plan_funds")
        funds = AnalyticAccount.search(
            [("root_plan_id", "=", funds_plan.id)], order="code"
        )

        sources_plan = request.env.ref("account_analytic_kmitl.analytic_plan_sources")
        sources = AnalyticAccount.search(
            [("root_plan_id", "=", sources_plan.id)], order="code"
        )

        # Build domain based on filters
        domain = self._build_project_domain(**kw)

        # Get projects with pagination
        page = int(kw.get("page", 1))
        per_page = 20
        offset = (page - 1) * per_page

        projects_count = Project.search_count(domain)
        projects = Project.search(
            domain, limit=per_page, offset=offset, order="id desc"
        )

        # Calculate summary statistics
        all_projects_domain = self._build_project_domain(
            fiscal_year_id=kw.get("fiscal_year_id"),
            department_id=kw.get("department_id"),
            activity_id=kw.get("activity_id"),
            fund_id=kw.get("fund_id"),
            source_id=kw.get("source_id"),
        )
        all_projects = Project.search(all_projects_domain)
        summary = self._calculate_summary(all_projects)

        # Status counts for legend
        status_counts = self._get_status_counts(all_projects_domain, Project)

        # Pagination
        total_pages = (projects_count + per_page - 1) // per_page if projects_count else 1

        # Chart data
        chart_data = self._prepare_chart_data(all_projects)

        return {
            # Filter options
            "fiscal_years": fiscal_years,
            "activities": activities,
            "departments": departments,
            "funds": funds,
            "sources": sources,
            # Current filter values
            "current_fiscal_year_id": kw.get("fiscal_year_id", ""),
            "current_department_id": kw.get("department_id", ""),
            "current_activity_id": kw.get("activity_id", ""),
            "current_fund_id": kw.get("fund_id", ""),
            "current_source_id": kw.get("source_id", ""),
            "current_state": kw.get("state", "all"),
            "current_search": kw.get("search", ""),
            # Projects data
            "projects": projects,
            "projects_count": projects_count,
            # Summary data
            "summary": summary,
            "status_counts": status_counts,
            # Chart data (JSON for JavaScript)
            "chart_data": chart_data,
            # Pagination
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            # States for tabs
            "states": [
                ("all", "ทั้งหมด"),
                ("draft", "Draft"),
                ("new", "ยังไม่เริ่ม"),
                ("in_progress", "กำลังดำเนินการ"),
                ("complete", "เสร็จสิ้น"),
                ("cancel", "ยกเลิก"),
            ],
        }

    def _build_project_domain(self, **kw):
        """Build search domain from filter parameters"""
        domain = [("active", "=", True)]

        if kw.get("fiscal_year_id"):
            domain.append(("account_fiscal_year_id", "=", int(kw["fiscal_year_id"])))

        # Filter by analytic distribution JSON field for 4D dimensions
        if kw.get("department_id"):
            dept_id = str(kw["department_id"])
            domain.append(("analytic_distribution", "ilike", dept_id))

        if kw.get("activity_id"):
            act_id = str(kw["activity_id"])
            domain.append(("analytic_distribution", "ilike", act_id))

        if kw.get("fund_id"):
            fund_id = str(kw["fund_id"])
            domain.append(("analytic_distribution", "ilike", fund_id))

        if kw.get("source_id"):
            source_id = str(kw["source_id"])
            domain.append(("analytic_distribution", "ilike", source_id))

        state = kw.get("state", "all")
        if state and state != "all":
            domain.append(("state", "=", state))

        if kw.get("search"):
            domain.insert(0, "|")
            domain.append(("name", "ilike", kw["search"]))
            domain.append(("key", "ilike", kw["search"]))

        return domain

    def _calculate_summary(self, projects):
        """Calculate summary statistics"""
        total_count = len(projects)
        total_budget = sum(
            sum(p.amount for p in proj.plan_ids) for proj in projects
        )
        completed_count = len(projects.filtered(lambda p: p.state == "complete"))

        return {
            "total_count": total_count,
            "total_budget": total_budget,
            "completed_count": completed_count,
            "completion_rate": (
                (completed_count / total_count * 100) if total_count else 0
            ),
        }

    def _get_status_counts(self, base_domain, Project):
        """Get count of projects by status"""
        states = ["draft", "new", "in_progress", "on_hold", "complete", "cancel"]

        counts = {}
        for state in states:
            domain = base_domain + [("state", "=", state)]
            counts[state] = Project.search_count(domain)

        return counts

    def _prepare_chart_data(self, projects):
        """Prepare data for charts (bar chart, trend line)"""
        # Budget by department
        dept_budgets = {}
        for proj in projects:
            dept_name = (
                proj.department_analytic_id.name
                or proj.department_id.name
                or "ไม่ระบุ"
            )
            budget = sum(p.amount for p in proj.plan_ids)
            dept_budgets[dept_name] = dept_budgets.get(dept_name, 0) + budget

        # Sort by budget descending, take top 10
        sorted_depts = sorted(
            dept_budgets.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Monthly trend (projects by month based on date_start)
        monthly_trend = {}
        for proj in projects:
            if proj.date_start:
                month_key = proj.date_start.strftime("%Y-%m")
                monthly_trend[month_key] = monthly_trend.get(month_key, 0) + 1

        # Sort and take last 12 months
        sorted_months = sorted(monthly_trend.keys())[-12:]

        return json.dumps(
            {
                "budget_by_department": {
                    "labels": [d[0] for d in sorted_depts],
                    "data": [d[1] for d in sorted_depts],
                },
                "monthly_trend": {
                    "labels": sorted_months,
                    "data": [monthly_trend.get(m, 0) for m in sorted_months],
                },
            }
        )
