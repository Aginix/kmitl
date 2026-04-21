from collections import defaultdict

from odoo import http
from odoo.http import request


class PurchaseRequestDashboardController(http.Controller):

    STATE_LABELS = {
        "draft": "ฉบับร่าง",
        "to_examine": "ตรวจสอบ",
        "to_verify": "ตรวจรับ",
        "to_approve": "รออนุมัติ",
        "approved": "อนุมัติแล้ว",
        "in_progress": "กำลังดำเนินการ",
        "done": "เสร็จสิ้น",
        "rejected": "ปฏิเสธ",
    }

    STATE_COLORS = {
        "draft": "#6c757d",
        "to_examine": "#17a2b8",
        "to_verify": "#0dcaf0",
        "to_approve": "#ffc107",
        "approved": "#198754",
        "in_progress": "#0d6efd",
        "done": "#28a745",
        "rejected": "#dc3545",
    }

    # Thai fiscal year months (Oct - Sep)
    FISCAL_MONTHS = [
        (10, "ต.ค."),
        (11, "พ.ย."),
        (12, "ธ.ค."),
        (1, "ม.ค."),
        (2, "ก.พ."),
        (3, "มี.ค."),
        (4, "เม.ย."),
        (5, "พ.ค."),
        (6, "มิ.ย."),
        (7, "ก.ค."),
        (8, "ส.ค."),
        (9, "ก.ย."),
    ]

    @http.route(
        "/purchase_request/dashboard/data",
        type="json",
        auth="user",
    )
    def get_dashboard_data(
        self, fiscal_year_id=None, department_id=None, source_id=None, **kw
    ):
        # Filter options
        fiscal_years = request.env["account.fiscal.year"].search(
            [], order="date_from desc"
        )
        fiscal_year_options = [
            {"id": fy.id, "name": fy.name} for fy in fiscal_years
        ]

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

        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = fiscal_years[0].id

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

    def _filter_by_analytic(self, records, department_id, source_id):
        """Filter records by department and source analytic dimensions."""
        department_ids = set()
        if department_id:
            root_dept = request.env["account.analytic.account"].browse(department_id)
            if root_dept.exists():
                child_depts = request.env["account.analytic.account"].search(
                    [("parent_path", "like", root_dept.parent_path + "%")]
                )
                department_ids = set(child_depts.ids)

        if not department_ids and not source_id:
            return records

        filtered = request.env[records._name]
        for rec in records:
            if department_ids and rec.department_analytic_id.id not in department_ids:
                continue
            if source_id and rec.source_analytic_id.id != source_id:
                continue
            filtered |= rec
        return filtered

    def _get_dashboard_stats(self, fiscal_year_id, department_id, source_id):
        domain = []
        if fiscal_year_id:
            domain.append(("account_fiscal_year_id", "=", fiscal_year_id))

        requests = request.env["purchase.request"].search(domain)
        requests = self._filter_by_analytic(requests, department_id, source_id)

        # Summary counts
        total_count = len(requests)
        total_amount = sum(requests.mapped("estimated_cost"))

        state_counts = {}
        for state_key in self.STATE_LABELS:
            state_requests = requests.filtered(lambda r, s=state_key: r.state == s)
            state_counts[state_key] = len(state_requests)

        # Pie chart data
        state_pie_data = []
        for state_key, label in self.STATE_LABELS.items():
            count = state_counts.get(state_key, 0)
            if count > 0:
                state_pie_data.append({
                    "name": label,
                    "value": count,
                    "itemStyle": {"color": self.STATE_COLORS.get(state_key)},
                })

        # Stacked bar by department
        dept_bar_data = self._get_dept_bar_data(requests)

        # Stacked bar by fiscal year (ignore fiscal year filter for this chart)
        fy_bar_data = self._get_fy_bar_data(department_id, source_id)

        # Line trend by month
        trend_line_data = self._get_trend_line_data(requests, fiscal_year_id)

        # Table data
        table_data = []
        for pr in requests[:100]:
            table_data.append({
                "id": pr.id,
                "name": pr.name,
                "title": pr.title or pr.description or "",
                "estimated_cost": pr.estimated_cost,
                "state": pr.state,
                "state_display": self.STATE_LABELS.get(pr.state, pr.state),
                "department": (
                    pr.department_analytic_id.name
                    if pr.department_analytic_id
                    else "-"
                ),
                "fiscal_year": (
                    pr.account_fiscal_year_id.name
                    if pr.account_fiscal_year_id
                    else "-"
                ),
            })

        return {
            "total_count": total_count,
            "total_amount": total_amount,
            "pending_approval_count": state_counts.get("to_approve", 0),
            "approved_count": state_counts.get("approved", 0),
            "in_progress_count": state_counts.get("in_progress", 0),
            "rejected_count": state_counts.get("rejected", 0),
            "state_pie_data": state_pie_data,
            "dept_bar_data": dept_bar_data,
            "fy_bar_data": fy_bar_data,
            "trend_line_data": trend_line_data,
            "table_data": table_data,
        }

    def _get_dept_bar_data(self, requests):
        """Group requests by root department and state for stacked bar chart."""
        dept_state = defaultdict(lambda: defaultdict(int))
        for pr in requests:
            dept = pr.department_analytic_id
            if not dept:
                continue
            # Walk up to root department
            root = dept
            while root.parent_id:
                root = root.parent_id
            dept_state[root.name][pr.state] += 1

        departments = sorted(dept_state.keys())
        series = []
        for state_key, label in self.STATE_LABELS.items():
            data = [dept_state[d].get(state_key, 0) for d in departments]
            if any(data):
                series.append({
                    "name": label,
                    "data": data,
                    "color": self.STATE_COLORS.get(state_key),
                })

        return {"departments": departments, "series": series}

    def _get_fy_bar_data(self, department_id, source_id):
        """Get stacked bar data across all fiscal years (last 5)."""
        fiscal_years = request.env["account.fiscal.year"].search(
            [], order="date_from desc", limit=5
        )
        if not fiscal_years:
            return {"fiscal_years": [], "series": []}

        all_requests = request.env["purchase.request"].search(
            [("account_fiscal_year_id", "in", fiscal_years.ids)]
        )
        all_requests = self._filter_by_analytic(
            all_requests, department_id, source_id
        )

        fy_state = defaultdict(lambda: defaultdict(int))
        for pr in all_requests:
            fy_name = pr.account_fiscal_year_id.name or "-"
            fy_state[fy_name][pr.state] += 1

        fy_names = [fy.name for fy in reversed(fiscal_years)]
        series = []
        for state_key, label in self.STATE_LABELS.items():
            data = [fy_state[fy].get(state_key, 0) for fy in fy_names]
            if any(data):
                series.append({
                    "name": label,
                    "data": data,
                    "color": self.STATE_COLORS.get(state_key),
                })

        return {"fiscal_years": fy_names, "series": series}

    def _get_trend_line_data(self, requests, fiscal_year_id):
        """Monthly trend for current and previous fiscal years."""
        fiscal_years = request.env["account.fiscal.year"].search(
            [], order="date_from desc", limit=3
        )
        if not fiscal_years:
            return {"months": [], "series": []}

        months = [m[1] for m in self.FISCAL_MONTHS]
        month_nums = [m[0] for m in self.FISCAL_MONTHS]

        series = []
        for fy in reversed(fiscal_years):
            fy_requests = requests.filtered(
                lambda r, f=fy: r.account_fiscal_year_id.id == f.id
            )
            if not fy_requests and fy.id != fiscal_year_id:
                continue
            month_counts = defaultdict(int)
            for pr in fy_requests:
                if pr.date_start:
                    month_counts[pr.date_start.month] += 1
            data = [month_counts.get(m, 0) for m in month_nums]
            series.append({"name": fy.name, "data": data})

        return {"months": months, "series": series}
