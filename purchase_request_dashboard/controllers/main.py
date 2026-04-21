from collections import defaultdict

from odoo import http
from odoo.http import request


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
    def get_dashboard_data(self, fiscal_year_id=None, source_id=None, **kw):
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

        # Build caches for root lookups
        budget_cache = self._build_root_budget_account_map(records)
        dept_cache = self._build_root_department_map(records)

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
                records
            ),
            "chart2_purchase_type_pie": self._get_chart2_purchase_type_pie(records),
            "chart3_expense_type_by_month": self._get_chart3_expense_type_by_month(
                records, budget_cache
            ),
            "chart4_approved_trend": self._get_chart4_approved_trend(records),
            "chart5_purchase_type_by_dept": self._get_chart5_purchase_type_by_dept(
                records, dept_cache
            ),
            "chart6_expense_type_by_dept": self._get_chart6_expense_type_by_dept(
                records, budget_cache, dept_cache
            ),
        }

    def _filter_by_source(self, records, source_id):
        """Filter records by source analytic dimension."""
        if not source_id:
            return records
        filtered = request.env[records._name]
        for rec in records:
            if rec.source_analytic_id.id == source_id:
                filtered |= rec
        return filtered

    def _build_root_budget_account_map(self, records):
        """Cache budget_account_id → root budget account name."""
        cache = {}
        for pr in records:
            ba = pr.budget_account_id
            if not ba or ba.id in cache:
                continue
            root = ba
            while root.parent_id:
                root = root.parent_id
            cache[ba.id] = root.name
        return cache

    def _build_root_department_map(self, records):
        """Cache department_analytic_id → root department name."""
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

    def _get_summary_boxes(self, records):
        """Return list of 8 summary box data."""
        boxes = []
        for state_key, label in self.SUMMARY_STATES:
            if state_key == "draft":
                # Include to_examine in draft
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
        # Box 8: total amount
        boxes.append({
            "label": "ยอดเงินรวมทั้งหมด",
            "state": "total",
            "count": None,
            "amount": sum(records.mapped("estimated_cost")),
        })
        return boxes

    def _get_chart1_purchase_type_by_month(self, records):
        """Stacked bar: estimated_cost by purchase_type, grouped by month."""
        month_labels = [m[1] for m in self.FISCAL_MONTHS]
        month_nums = [m[0] for m in self.FISCAL_MONTHS]

        type_month_amounts = defaultdict(lambda: defaultdict(float))
        for pr in records:
            if not pr.date_start or not pr.purchase_type_id:
                continue
            type_name = pr.purchase_type_id.name
            month = pr.date_start.month
            type_month_amounts[type_name][month] += pr.estimated_cost

        purchase_types = sorted(type_month_amounts.keys())
        series = []
        for pt in purchase_types:
            data = [type_month_amounts[pt].get(m, 0) for m in month_nums]
            series.append({"name": pt, "data": data})

        return {"months": month_labels, "series": series}

    def _get_chart2_purchase_type_pie(self, records):
        """Pie: estimated_cost grouped by purchase_type."""
        type_data = defaultdict(lambda: {"amount": 0, "id": None})
        for pr in records:
            if not pr.purchase_type_id:
                continue
            key = pr.purchase_type_id.name
            type_data[key]["amount"] += pr.estimated_cost
            type_data[key]["id"] = pr.purchase_type_id.id

        pie_data = []
        for name, info in sorted(type_data.items()):
            if info["amount"] > 0:
                pie_data.append({
                    "name": name,
                    "value": info["amount"],
                    "purchase_type_id": info["id"],
                })
        return pie_data

    def _get_chart3_expense_type_by_month(self, records, budget_cache):
        """Stacked bar: estimated_cost by root budget_account, grouped by month."""
        month_labels = [m[1] for m in self.FISCAL_MONTHS]
        month_nums = [m[0] for m in self.FISCAL_MONTHS]

        expense_month_amounts = defaultdict(lambda: defaultdict(float))
        for pr in records:
            if not pr.date_start or not pr.budget_account_id:
                continue
            expense_name = budget_cache.get(pr.budget_account_id.id)
            if not expense_name:
                continue
            month = pr.date_start.month
            expense_month_amounts[expense_name][month] += pr.estimated_cost

        expense_types = sorted(expense_month_amounts.keys())
        series = []
        for et in expense_types:
            data = [expense_month_amounts[et].get(m, 0) for m in month_nums]
            series.append({"name": et, "data": data})

        return {"months": month_labels, "series": series}

    def _get_chart4_approved_trend(self, records):
        """Stacked line: estimated_cost by purchase_type for approved records."""
        month_labels = [m[1] for m in self.FISCAL_MONTHS]
        month_nums = [m[0] for m in self.FISCAL_MONTHS]

        approved_recs = records.filtered(
            lambda r: r.state in ("approved", "in_progress", "done")
        )

        type_month_amounts = defaultdict(lambda: defaultdict(float))
        for pr in approved_recs:
            if not pr.date_approved or not pr.purchase_type_id:
                continue
            type_name = pr.purchase_type_id.name
            month = pr.date_approved.month
            type_month_amounts[type_name][month] += pr.estimated_cost

        purchase_types = sorted(type_month_amounts.keys())
        series = []
        for pt in purchase_types:
            data = [type_month_amounts[pt].get(m, 0) for m in month_nums]
            series.append({"name": pt, "data": data})

        return {"months": month_labels, "series": series}

    def _get_chart5_purchase_type_by_dept(self, records, dept_cache):
        """Stacked bar: estimated_cost by purchase_type, grouped by department."""
        dept_type_amounts = defaultdict(lambda: defaultdict(float))
        for pr in records:
            if not pr.department_analytic_id or not pr.purchase_type_id:
                continue
            dept_name = dept_cache.get(pr.department_analytic_id.id)
            if not dept_name:
                continue
            dept_type_amounts[dept_name][pr.purchase_type_id.name] += (
                pr.estimated_cost
            )

        departments = sorted(dept_type_amounts.keys())
        all_types = set()
        for dept_data in dept_type_amounts.values():
            all_types.update(dept_data.keys())
        all_types = sorted(all_types)

        series = []
        for pt in all_types:
            data = [dept_type_amounts[d].get(pt, 0) for d in departments]
            if any(data):
                series.append({"name": pt, "data": data})

        return {"departments": departments, "series": series}

    def _get_chart6_expense_type_by_dept(self, records, budget_cache, dept_cache):
        """Stacked bar: estimated_cost by root budget_account, grouped by dept."""
        dept_expense_amounts = defaultdict(lambda: defaultdict(float))
        for pr in records:
            if not pr.department_analytic_id or not pr.budget_account_id:
                continue
            dept_name = dept_cache.get(pr.department_analytic_id.id)
            expense_name = budget_cache.get(pr.budget_account_id.id)
            if not dept_name or not expense_name:
                continue
            dept_expense_amounts[dept_name][expense_name] += pr.estimated_cost

        departments = sorted(dept_expense_amounts.keys())
        all_expenses = set()
        for dept_data in dept_expense_amounts.values():
            all_expenses.update(dept_data.keys())
        all_expenses = sorted(all_expenses)

        series = []
        for et in all_expenses:
            data = [dept_expense_amounts[d].get(et, 0) for d in departments]
            if any(data):
                series.append({"name": et, "data": data})

        return {"departments": departments, "series": series}
