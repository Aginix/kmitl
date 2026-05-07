from collections import defaultdict

from odoo import http
from odoo.http import request
from collections import defaultdict


class PurchaseRequestDashboardController(http.Controller):

    SUMMARY_STATES = [
        ("draft", "ร่าง"),
        ("to_verify", "รอจองเงิน"),
        ("to_approve", "รออนุมัติ"),
        ("approved", "อนุมัติแล้ว"),
        ("in_progress", "อยู่ระหว่างจัดซื้อ/จ้าง"),
        ("done", "จัดซื้อ/จ้างเสร็จสิ้น"),
        ("rejected", "ยกเลิก"),
    ]

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
        """Return all data needed by the dashboard frontend.

        Returns dict with keys:
            filter_options  – available fiscal years and source options
            filters         – currently active filter IDs
            summary_boxes   – list of 8 state-based summary cards (always all records)
            chart1..chart6  – chart-specific data structures (filtered by state)
        """
        # Filter options
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
            source_id = sources[0].id

        # Fetch and filter records
        domain = []
        if fiscal_year_id:
            domain.append(("account_fiscal_year_id", "=", fiscal_year_id))

        records = request.env["purchase.request"].search(domain)
        records = self._filter_by_source(records, source_id)

        # Build caches for hierarchy lookups (avoids repeated DB traversal)
        budget_cache = self._build_root_budget_account_map(records)
        dept_cache = self._build_root_department_map(records)

        # State filtering for charts only (summary boxes always show all records).
        # The UI shows "ร่าง" (draft) as a single status, but internally Odoo uses
        # both "draft" and "to_examine" states, so selecting "draft" must include both.
        if selected_states:
            state_set = set(selected_states)
            if "draft" in state_set:
                state_set.add("to_examine")
            chart_records = records.filtered(lambda r: r.state in state_set)
        else:
            # Default: exclude rejected from charts (cancelled data shouldn't pollute charts)
            chart_records = records.filtered(lambda r: r.state != "rejected")

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
            "expense_type_pie": self._get_expense_type_pie(
                chart_records, budget_cache
            ),
            "chart3_expense_type_by_month": self._get_chart3_expense_type_by_month(
                chart_records, budget_cache
            ),
            "chart4_approved_trend": self._get_chart4_approved_trend(chart_records),
            "chart5_purchase_type_by_dept": self._get_chart5_purchase_type_by_dept(
                chart_records, dept_cache
            ),
            "chart6_expense_type_by_dept": self._get_chart6_expense_type_by_dept(
                chart_records, budget_cache, dept_cache
            ),
            "chart7_leadtime_heatmap": self._get_chart7_leadtime_heatmap(
                fiscal_year_id=fiscal_year_id
            ),
        }

    # ──────────────────────────────────────────────────────────────────
    # Record filtering helpers
    # ──────────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────────
    # Hierarchy cache builders
    # ──────────────────────────────────────────────────────────────────

    def _build_root_budget_account_map(self, records):
        """Cache budget_account_id → parent budget account name (expense category).

        Budget accounts selectable in purchase requests are leaf-level nodes.
        Their direct parent represents the expense category we want for charts
        (e.g., "ครุภัณฑ์", "สิ่งก่อสร้าง", "ค่าตอบแทน").
        We go up exactly one level. Falls back to self if no parent exists.
        """
        cache = {}
        for pr in records:
            ba = pr.budget_account_id
            if not ba or ba.id in cache:
                continue
            category = ba.parent_id or ba
            cache[ba.id] = category.name
        return cache

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

    # ──────────────────────────────────────────────────────────────────
    # Shared aggregation helpers
    # ──────────────────────────────────────────────────────────────────

    def _aggregate_by_month(self, records, category_fn, date_fn):
        """Aggregate estimated_cost by category and fiscal month.

        Common pattern for charts 1, 3, 4: group amounts into a 2D dict
        {category_name: {month_num: total_amount}}, then build series list.

        Args:
            records: purchase.request recordset to aggregate
            category_fn: callable(pr) -> str or None (series name)
            date_fn: callable(pr) -> date or None (date whose month to use)
        Returns:
            dict: {"months": [label strings], "series": [{"name": ..., "data": [...]}]}
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

        Common pattern for charts 5, 6: group amounts into a 2D dict
        {dept_name: {category_name: total_amount}}, then build series list.

        Args:
            records: purchase.request recordset
            category_fn: callable(pr) -> str or None (series name)
            dept_cache: dict mapping department_analytic_id -> department name
        Returns:
            dict: {"departments": [names], "series": [{"name": ..., "data": [...]}]}
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

    def _get_summary_boxes(self, records):
        """Return list of 8 summary box data (7 states + 1 total)."""
        boxes = []
        for state_key, label in self.SUMMARY_STATES:
            if state_key == "draft":
                # "draft" box includes both "draft" and "to_examine" states
                state_recs = records.filtered(
                    lambda r: r.state in ("draft", "to_examine")
                )
            else:
                state_recs = records.filtered(
                    lambda r, s=state_key: r.state == s
                )
            boxes.append({
                "label": label,
                "state": state_key,
                "count": len(state_recs),
                "amount": sum(state_recs.mapped("estimated_cost")),
            })
        # Box 8: total amount across all states
        boxes.append({
            "label": "ยอดเงินรวมทั้งหมด",
            "state": "total",
            "count": None,
            "amount": sum(records.mapped("estimated_cost")),
        })
        return boxes

    # ──────────────────────────────────────────────────────────────────
    # Chart data builders
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

    def _get_expense_type_pie(self, records, budget_cache):
        """Pie: estimated_cost grouped by expense category (budget_account parent).

        Returns list of dicts with budget_account_ids for click-through navigation.
        Each slice aggregates all budget accounts that share the same parent category.
        """
        cat_data = defaultdict(lambda: {"amount": 0, "account_ids": []})
        for pr in records:
            if not pr.budget_account_id:
                continue
            cat_name = budget_cache.get(pr.budget_account_id.id)
            if not cat_name:
                continue
            cat_data[cat_name]["amount"] += pr.estimated_cost
            if pr.budget_account_id.id not in cat_data[cat_name]["account_ids"]:
                cat_data[cat_name]["account_ids"].append(pr.budget_account_id.id)

        return [
            {
                "name": name,
                "value": info["amount"],
                "budget_account_ids": info["account_ids"],
            }
            for name, info in sorted(cat_data.items())
            if info["amount"] > 0
        ]

    def _get_chart3_expense_type_by_month(self, records, budget_cache):
        """Stacked bar: estimated_cost by expense category, grouped by fiscal month."""
        return self._aggregate_by_month(
            records,
            category_fn=lambda pr: (
                budget_cache.get(pr.budget_account_id.id)
                if pr.budget_account_id
                else None
            ),
            date_fn=lambda pr: pr.date_start,
        )

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

    def _get_chart6_expense_type_by_dept(self, records, budget_cache, dept_cache):
        """Stacked bar: estimated_cost by expense category, grouped by department."""
        return self._aggregate_by_department(
            records,
            category_fn=lambda pr: (
                budget_cache.get(pr.budget_account_id.id)
                if pr.budget_account_id
                else None
            ),
            dept_cache=dept_cache,
        )

    def _get_chart7_leadtime_heatmap(self, fiscal_year_id=None):
        TRACKED_TRANSITIONS = [
            ('draft',       'to_verify',   'จัดทำคำขอ'),
            ('to_verify',   'to_approve',  'จองเงิน'),
            ('to_approve',  'approved',    'ขออนุมัติคำขอ'),
            ('approved',    'in_progress', 'จัดซื้อจัดจ้าง'),
            ('in_progress', 'done',        'จัดทำสัญญา'),
        ]

        res_ids = None
        if fiscal_year_id:
            prs = request.env['purchase.request'].search(
                [('account_fiscal_year_id', '=', fiscal_year_id)]
            )
            res_ids = prs.ids

        log = request.env['state.leadtime.log'].sudo()
        data = []

        for from_state, to_state, label in TRACKED_TRANSITIONS:
            stats = log.get_stats(
                res_model='purchase.request',
                from_state=from_state,
                to_state=to_state,
                res_ids=res_ids,
            )
            data.append({
                'name': label,
                'from_state': from_state,
                'to_state': to_state,
                'avg': round(stats['avg_minutes'], 2),
                'total': round(stats['total_minutes'], 2),
                'count': stats['count'],
            })

        return data
