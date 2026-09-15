from collections import defaultdict

from odoo import http
from odoo.http import request

# Core summary states with explicit sequence numbers (gaps allow extensions to
# insert between them). Extensions append (seq, state_key, label) tuples here.
_BASE_SUMMARY_STATES = [
    (10, "draft",       "ฉบับร่าง"),
    (20, "to_verify",   "รอธุรการตรวจสอบ"),
    # seq 25: to_verify_budget (purchase_request_dashboard_budget)
    (40, "to_approve",  "รอส่งขอความเห็นชอบให้จัดหา"),
    # seq 42: sent (purchase_request_dashboard_sarabun)
    # seq 45: in_egp (purchase_request_dashboard_egp)
    (50, "in_approval", "อยู่ระหว่างจัดทำ พจ.1"),
    (60, "in_progress", "อยู่ระหว่างจัดซื้อจัดจ้าง"),
    (70, "done",        "จัดซื้อจัดจ้างเสร็จสิ้น"),
    (80, "cancelled",   "ยกเลิก"),
    (90, "rejected",    "ปฎิเสธ"),
]
_EXTRA_SUMMARY_STATES = []


class PurchaseRequestDashboardController(http.Controller):

    # States hidden from the dashboard: 'approved' is a transient bucket that
    # immediately transitions to in_progress, so records shouldn't linger there.
    HIDDEN_STATES = ("approved",)
    # States excluded from charts by default (when no state box is selected).
    DEFAULT_CHART_EXCLUDED_STATES = ("approved", "cancelled", "rejected")

    # Thai fiscal year runs Oct → Sep (e.g., FY 2569 = Oct 2025 - Sep 2026)
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

    # ──────────────────────────────────────────────────────────────────
    # Main endpoint
    # ──────────────────────────────────────────────────────────────────

    @http.route(
        "/purchase_request/dashboard/data",
        type="json",
        auth="user",
    )
    def get_dashboard_data(
        self, fiscal_year_id=None, source_id=None, selected_states=None, **kw
    ):
        """Return core dashboard data (filters, summary boxes, chart 1/2/4/5).

        Extension modules (dashboard_budget, dashboard_leadtime) expose their
        own endpoints and register chart cards through the frontend registry.
        """
        fiscal_years = request.env["account.fiscal.year"].search(
            [], order="date_from desc"
        )
        fiscal_year_options = [
            {"id": fy.id, "name": fy.name} for fy in fiscal_years
        ]

        sources = request.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "sources")], order="code"
        )
        source_options = [
            {"id": src.id, "name": src.name, "code": src.code} for src in sources
        ]

        # Default to first options (required filters)
        if not fiscal_year_id and fiscal_years:
            fiscal_year_id = fiscal_years[0].id
        if not source_id and sources:
            default_source = sources.filtered(lambda s: s.code == "2")
            source_id = (default_source[:1] or sources[:1]).id

        records = self._search_prs(fiscal_year_id, source_id)
        chart_records = self._filter_by_selected_states(records, selected_states)
        dept_cache = self._build_root_department_map(chart_records)

        return {
            "filter_options": {
                "fiscal_years": fiscal_year_options,
                "sources": source_options,
            },
            "filters": {
                "fiscal_year_id": fiscal_year_id,
                "source_id": source_id,
            },
            "summary_boxes": self._get_summary_boxes(records),
            "chart1_purchase_type_by_month": self._get_chart1_purchase_type_by_month(
                chart_records
            ),
            "chart2_purchase_type_pie": self._get_chart2_purchase_type_pie(
                chart_records
            ),
            "chart4_approved_trend": self._get_chart4_approved_trend(chart_records),
            "chart5_purchase_type_by_dept": self._get_chart5_purchase_type_by_dept(
                chart_records, dept_cache
            ),
        }

    # ──────────────────────────────────────────────────────────────────
    # Shared helpers (also called by extension controllers)
    # ──────────────────────────────────────────────────────────────────

    def _search_prs(self, fiscal_year_id, source_id):
        """Fetch purchase requests matching the shared dashboard filters.

        Applied to every chart across core and extensions: fiscal year via
        domain, source via analytic-JSON filter, then the transient 'approved'
        state is dropped so records don't leak into that hidden bucket.
        """
        domain = []
        if fiscal_year_id:
            domain.append(("account_fiscal_year_id", "=", fiscal_year_id))
        records = request.env["purchase.request"].search(domain)
        records = self._filter_by_source(records, source_id)
        return records.filtered(lambda r: r.state not in self.HIDDEN_STATES)

    def _filter_by_selected_states(self, records, selected_states):
        """Apply the summary-box state filter to a set of records.

        When the user has clicked one or more summary boxes, narrow charts to
        those states. When nothing is selected, exclude the noisy default set
        (approved/cancelled/rejected) so charts show only in-flight work.
        """
        if selected_states:
            state_set = set(selected_states)
            return records.filtered(lambda r: r.state in state_set)
        excluded = self.DEFAULT_CHART_EXCLUDED_STATES
        return records.filtered(lambda r: r.state not in excluded)

    def _filter_by_source(self, records, source_id):
        """Filter records by source analytic dimension.

        Source is stored in the analytic_distribution JSON field, so standard
        ORM domain filtering isn't straightforward. We filter in Python instead.
        """
        if not source_id:
            return records
        filtered = request.env[records._name]
        for rec in records:
            if rec.source_analytic_id.id == source_id:
                filtered |= rec
        return filtered

    def _build_root_department_map(self, records):
        """Cache department_analytic_id → root department name.

        Department analytic accounts form a multi-level hierarchy.
        We traverse all the way up to the root (no parent) to get the
        top-level department name for chart grouping.
        """
        cache = {}
        for pr in records:
            dept = pr.department_analytic_id
            if not dept or dept.id in cache:
                continue
            root = dept
            while root.parent_id:
                root = root.parent_id
            cache[dept.id] = root.name
        return cache

    def _aggregate_by_month(self, records, category_fn, date_fn):
        """Aggregate estimated_cost by category and fiscal month.

        Common pattern for stacked-bar-by-month charts: group amounts into a 2D
        dict {category_name: {month_num: total_amount}}, then build series list.
        """
        month_labels = [m[1] for m in self.FISCAL_MONTHS]
        month_nums = [m[0] for m in self.FISCAL_MONTHS]

        amounts = defaultdict(lambda: defaultdict(float))
        for pr in records:
            cat = category_fn(pr)
            dt = date_fn(pr)
            if not cat or not dt:
                continue
            amounts[cat][dt.month] += pr.estimated_cost

        series = []
        for name in sorted(amounts.keys()):
            data = [amounts[name].get(m, 0) for m in month_nums]
            series.append({"name": name, "data": data})

        return {"months": month_labels, "series": series}

    def _aggregate_by_department(self, records, category_fn, dept_cache):
        """Aggregate estimated_cost by department and category.

        Common pattern for stacked-bar-by-department charts.
        """
        dept_cat_amounts = defaultdict(lambda: defaultdict(float))
        for pr in records:
            if not pr.department_analytic_id:
                continue
            dept_name = dept_cache.get(pr.department_analytic_id.id)
            cat = category_fn(pr)
            if not dept_name or not cat:
                continue
            dept_cat_amounts[dept_name][cat] += pr.estimated_cost

        departments = sorted(dept_cat_amounts.keys())
        all_cats = sorted({c for d in dept_cat_amounts.values() for c in d})

        series = []
        for cat in all_cats:
            data = [dept_cat_amounts[d].get(cat, 0) for d in departments]
            if any(data):
                series.append({"name": cat, "data": data})

        return {"departments": departments, "series": series}

    # ──────────────────────────────────────────────────────────────────
    # Summary boxes
    # ──────────────────────────────────────────────────────────────────

    def _get_all_summary_states(self):
        """Merge core and extension-registered summary states, sorted by sequence."""
        combined = list(_BASE_SUMMARY_STATES) + list(_EXTRA_SUMMARY_STATES)
        combined.sort(key=lambda x: x[0])
        return [(key, label) for _, key, label in combined]

    def _get_summary_boxes(self, records):
        """Return list of summary box data (state buckets + total)."""
        boxes = []
        for state_key, label in self._get_all_summary_states():
            state_recs = records.filtered(lambda r, s=state_key: r.state == s)
            boxes.append({
                "label": label,
                "state": state_key,
                "count": len(state_recs),
                "amount": sum(state_recs.mapped("estimated_cost")),
            })
        boxes.append({
            "label": "ยอดเงินรวมทั้งหมด",
            "state": "total",
            "count": None,
            "amount": sum(records.mapped("estimated_cost")),
        })
        return boxes

    # ──────────────────────────────────────────────────────────────────
    # Chart data builders (core only)
    # ──────────────────────────────────────────────────────────────────

    def _get_chart1_purchase_type_by_month(self, records):
        """Stacked bar: estimated_cost by procurement type, grouped by fiscal month."""
        return self._aggregate_by_month(
            records,
            category_fn=lambda pr: (
                pr.procurement_type_id.name if pr.procurement_type_id else None
            ),
            date_fn=lambda pr: pr.date_start,
        )

    def _get_chart2_purchase_type_pie(self, records):
        """Pie/doughnut: estimated_cost grouped by procurement type.

        Returns list of dicts with procurement_type_id for click-through navigation.
        """
        type_data = defaultdict(lambda: {"amount": 0, "id": None})
        for pr in records:
            if not pr.procurement_type_id:
                continue
            key = pr.procurement_type_id.name
            type_data[key]["amount"] += pr.estimated_cost
            type_data[key]["id"] = pr.procurement_type_id.id

        pie_data = []
        for name, info in sorted(type_data.items()):
            if info["amount"] > 0:
                pie_data.append({
                    "name": name,
                    "value": info["amount"],
                    "procurement_type_id": info["id"],
                })
        return pie_data

    def _get_chart4_approved_trend(self, records):
        """Stacked line: estimated_cost trend by procurement type for approved records.

        Only includes records in approved/in_progress/done states.
        Uses date_approved (the date the request was approved) for the month axis.
        """
        approved_recs = records.filtered(
            lambda r: r.state in ("approved", "in_progress", "done")
        )
        return self._aggregate_by_month(
            approved_recs,
            category_fn=lambda pr: (
                pr.procurement_type_id.name if pr.procurement_type_id else None
            ),
            date_fn=lambda pr: pr.date_approved,
        )

    def _get_chart5_purchase_type_by_dept(self, records, dept_cache):
        """Stacked bar: estimated_cost by procurement type, grouped by department."""
        return self._aggregate_by_department(
            records,
            category_fn=lambda pr: (
                pr.procurement_type_id.name if pr.procurement_type_id else None
            ),
            dept_cache=dept_cache,
        )
