# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class ProcurementPlanDashboardController(http.Controller):

    STATE_LABELS = {
        "draft": "ฉบับร่าง",
        "new": "ยังไม่เริ่ม",
        "on_hold": "ชะลอโครงการ",
        "in_progress": "กำลังดำเนินการ",
        "done": "เสร็จสิ้น",
        "cancel": "ยกเลิก",
    }

    @http.route(
        "/procurement_plan/dashboard/data",
        type="json",
        auth="user",
    )
    def get_dashboard_data(
        self, fiscal_year_id=None, department_id=None, source_id=None, **kw
    ):
        """Get dashboard data for procurement plan."""
        # Get filter options
        fiscal_years = request.env["account.fiscal.year"].search(
            [], order="date_from desc"
        )
        fiscal_year_options = [{"id": fy.id, "name": fy.name} for fy in fiscal_years]

        # Get only root-level departments (no parent)
        departments = request.env["account.analytic.account"].search(
            [
                ("root_plan_id.code", "=", "departments"),
                ("parent_id", "=", False),
            ],
            order="code",
        )
        department_options = [
            {"id": dept.id, "name": dept.name, "code": dept.code}
            for dept in departments
        ]

        sources = request.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "sources")], order="code"
        )
        source_options = [
            {"id": src.id, "name": src.name, "code": src.code} for src in sources
        ]

        # Default to first fiscal year if not specified
        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = fiscal_years[0].id

        # Get dashboard statistics
        stats = self._get_dashboard_stats(fiscal_year_id, department_id, source_id)

        return {
            "filter_options": {
                "fiscal_years": fiscal_year_options,
                "departments": department_options,
                "sources": source_options,
            },
            "filters": {
                "fiscal_year_id": fiscal_year_id,
                "department_id": department_id,
                "source_id": source_id,
            },
            "stats": stats,
        }

    def _get_dashboard_stats(self, fiscal_year_id, department_id, source_id):
        """Calculate dashboard statistics from procurement.plan."""
        domain = []
        if fiscal_year_id:
            domain.append(("account_fiscal_year_id", "=", fiscal_year_id))

        plans = request.env["procurement.plan"].search(domain)

        # Get all child department IDs if department filter is set
        department_ids = set()
        if department_id:
            root_dept = request.env["account.analytic.account"].browse(department_id)
            if root_dept.exists():
                # Get all descendants using parent_path
                child_depts = request.env["account.analytic.account"].search(
                    [("parent_path", "like", root_dept.parent_path + "%")]
                )
                department_ids = set(child_depts.ids)

        # Filter by department and source (computed fields, filter in Python)
        if department_ids or source_id:
            filtered_plans = request.env["procurement.plan"]
            for plan in plans:
                if department_ids and plan.department_analytic_id.id not in department_ids:
                    continue
                if source_id and plan.source_analytic_id.id != source_id:
                    continue
                filtered_plans |= plan
            plans = filtered_plans

        # Calculate totals
        total_count = len(plans)
        total_amount = sum(plans.mapped("total_price"))

        # Count by state
        state_counts = {}
        state_amounts = {}
        for state_key in self.STATE_LABELS.keys():
            state_plans = plans.filtered(lambda p: p.state == state_key)
            state_counts[state_key] = len(state_plans)
            state_amounts[state_key] = sum(state_plans.mapped("total_price"))

        # Build pie chart data (by count)
        state_pie_data = []
        for state_key, label in self.STATE_LABELS.items():
            if state_counts.get(state_key, 0) > 0:
                state_pie_data.append({
                    "name": label,
                    "value": state_counts[state_key],
                })

        # Build table data
        table_data = []
        for plan in plans[:100]:  # Limit to 100 records
            table_data.append({
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "total_price": plan.total_price,
                "state": plan.state,
                "state_display": self.STATE_LABELS.get(plan.state, plan.state),
                "department": plan.department_analytic_id.complete_name or "-",
                "source": plan.source_analytic_id.name or "-",
                "method": plan.procurement_method_id.name
                if plan.procurement_method_id
                else "-",
            })

        return {
            "total_count": total_count,
            "total_amount": total_amount,
            "in_progress_count": state_counts.get("in_progress", 0),
            "done_count": state_counts.get("done", 0),
            "state_pie_data": state_pie_data,
            "table_data": table_data,
        }
