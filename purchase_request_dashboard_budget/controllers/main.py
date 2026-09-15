from collections import defaultdict

from odoo import http
from odoo.http import request

from odoo.addons.purchase_request_dashboard.controllers import main as dashboard_main
from odoo.addons.purchase_request_dashboard.controllers.main import (
    PurchaseRequestDashboardController,
)

# Insert the to_verify_budget state between to_verify (seq=20) and to_approve
# (seq=40). This runs at module import time, before any HTTP request is handled.
dashboard_main._EXTRA_SUMMARY_STATES.append(
    (25, "to_verify_budget", "รอจองงบประมาณ")
)


class PurchaseRequestDashboardBudgetController(http.Controller):
    """Endpoints for the three budget-account-driven chart cards.

    Each endpoint receives the same payload as the core endpoint
    (fiscal_year_id, source_id, selected_states) and reuses the base
    controller's filter helpers so results stay consistent with core charts.
    """

    # Reuse the base controller's helpers rather than re-implementing PR
    # search + source-JSON filter + selected-state gating.
    _base = PurchaseRequestDashboardController()

    # ──────────────────────────────────────────────────────────────────
    # Budget-account cache
    # ──────────────────────────────────────────────────────────────────

    def _build_root_budget_account_map(self, records):
        """Cache budget_account_id → parent budget account name (expense category).

        Budget accounts selectable in purchase requests are leaf-level nodes.
        Their direct parent represents the expense category we want for charts
        (e.g., "ครุภัณฑ์", "สิ่งก่อสร้าง", "ค่าตอบแทน").
        """
        cache = {}
        for pr in records:
            ba = pr.budget_account_id
            if not ba or ba.id in cache:
                continue
            category = ba.parent_id or ba
            cache[ba.id] = category.name
        return cache

    def _chart_records(self, fiscal_year_id, source_id, selected_states):
        records = self._base._search_prs(fiscal_year_id, source_id)
        return self._base._filter_by_selected_states(records, selected_states)

    # ──────────────────────────────────────────────────────────────────
    # Endpoints
    # ──────────────────────────────────────────────────────────────────

    @http.route(
        "/purchase_request/dashboard/expense_type_pie",
        type="json",
        auth="user",
    )
    def expense_type_pie(
        self, fiscal_year_id=None, source_id=None, selected_states=None, **kw
    ):
        """Pie slices grouped by parent budget account (expense category).

        Includes the underlying budget_account_ids per slice so the frontend
        can drill into a list view filtered on the leaf accounts.
        """
        records = self._chart_records(fiscal_year_id, source_id, selected_states)
        cache = self._build_root_budget_account_map(records)

        cat_data = defaultdict(lambda: {"amount": 0, "account_ids": set()})
        for pr in records:
            if not pr.budget_account_id:
                continue
            cat_name = cache.get(pr.budget_account_id.id)
            if not cat_name:
                continue
            cat_data[cat_name]["amount"] += pr.estimated_cost
            cat_data[cat_name]["account_ids"].add(pr.budget_account_id.id)

        return [
            {
                "name": name,
                "value": info["amount"],
                "budget_account_ids": list(info["account_ids"]),
            }
            for name, info in sorted(cat_data.items())
            if info["amount"] > 0
        ]

    @http.route(
        "/purchase_request/dashboard/expense_by_month",
        type="json",
        auth="user",
    )
    def expense_by_month(
        self, fiscal_year_id=None, source_id=None, selected_states=None, **kw
    ):
        """Stacked bar: estimated_cost by expense category, grouped by fiscal month."""
        records = self._chart_records(fiscal_year_id, source_id, selected_states)
        cache = self._build_root_budget_account_map(records)
        return self._base._aggregate_by_month(
            records,
            category_fn=lambda pr: (
                cache.get(pr.budget_account_id.id) if pr.budget_account_id else None
            ),
            date_fn=lambda pr: pr.date_start,
        )

    @http.route(
        "/purchase_request/dashboard/expense_by_dept",
        type="json",
        auth="user",
    )
    def expense_by_dept(
        self, fiscal_year_id=None, source_id=None, selected_states=None, **kw
    ):
        """Stacked bar: estimated_cost by expense category, grouped by department."""
        records = self._chart_records(fiscal_year_id, source_id, selected_states)
        cache = self._build_root_budget_account_map(records)
        dept_cache = self._base._build_root_department_map(records)
        return self._base._aggregate_by_department(
            records,
            category_fn=lambda pr: (
                cache.get(pr.budget_account_id.id) if pr.budget_account_id else None
            ),
            dept_cache=dept_cache,
        )
