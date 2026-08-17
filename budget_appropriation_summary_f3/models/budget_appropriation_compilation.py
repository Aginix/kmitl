# -*- coding: utf-8 -*-
import logging
from collections import defaultdict

from odoo import models

_logger = logging.getLogger(__name__)

# Source codes classified as government budget (เงินงบประมาณ)
BUDGET_SOURCE_CODES = ("1", "3", "5")

# Top-level revenue account codes in display order
REVENUE_CODES = ["43100 (ก)", "43300", "43400", "43500", "43700"]

# Top-level expense account codes in display order
EXPENSE_LEVEL0_CODES = ["51000", "52000", "53000", "54000", "55000", "07020"]


class BudgetAppropriationCompilation(models.Model):
    _inherit = "budget.appropriation.compilation"

    def get_f3_report_data(self):
        """Prepare F3 report data for QWeb rendering.

        Returns a dict with:
        - is_budget_source: bool - whether amounts go in the budget column
        - revenue_rows: list of {name, amount}
        - revenue_total: float
        - expenditure_rows: list of {level, prefix, name, amount}
        - expenditure_total: float
        """
        self.ensure_one()
        is_budget_source = self.source_analytic_id.code in BUDGET_SOURCE_CODES
        revenue_rows = self._get_f3_revenue_rows()
        revenue_total = sum(r["amount"] for r in revenue_rows)
        revenue_deduct = sum(
            a.amount_deduct for a in self.revenue_appropriation_ids
        )
        revenue_net = revenue_total - revenue_deduct
        expenditure_rows = self._get_f3_expenditure_rows()
        expenditure_total = sum(
            r["amount"] for r in expenditure_rows if r["level"] == 0
        )
        return {
            "is_budget_source": is_budget_source,
            "revenue_rows": revenue_rows,
            "revenue_total": revenue_total,
            "revenue_deduct": revenue_deduct,
            "revenue_net": revenue_net,
            "expenditure_rows": expenditure_rows,
            "expenditure_total": expenditure_total,
        }

    def _get_f3_revenue_rows(self):
        """Revenue summary grouped by top-level budget account.

        Only includes accounts matching REVENUE_CODES, displayed in that order.
        """
        lines = self.revenue_appropriation_ids.mapped("line_ids")
        if not lines:
            return []

        BudgetAccount = self.env["budget.account"]

        # Pre-fetch the fixed top-level accounts in one query
        top_accounts = BudgetAccount.search(
            [("code", "in", REVENUE_CODES)]
        )
        # Map every descendant to its top-level account
        root_map = {}
        for top in top_accounts:
            for desc in BudgetAccount.search(
                [("parent_path", "=like", f"{top.parent_path}%")]
            ):
                root_map[desc.id] = top

        # Aggregate line balances by top-level account
        account_totals = {}
        for line in lines:
            top = root_map.get(line.account_id.id)
            if not top:
                continue
            if top.code not in account_totals:
                account_totals[top.code] = {
                    "name": top.name,
                    "code": top.code,
                    "amount": 0.0,
                }
            account_totals[top.code]["amount"] += line.balance

        # Return in the fixed display order
        return [
            account_totals[code]
            for code in REVENUE_CODES
            if code in account_totals
        ]

    def _get_f3_expenditure_rows(self):
        """Expenditure summary with 4-level hierarchy.

        Level 0: expense type (51000, 52000, ...)
        Level 1: sub-category (children of level 0)
        Level 2: activity plan (children of activity_06 / activity_09)
        Level 3: fund
        """
        lines = self.expense_appropriation_ids.mapped("line_ids")
        if not lines:
            return []

        BudgetAccount = self.env["budget.account"]
        Analytic = self.env["account.analytic.account"]

        # --- Build budget account mappings ---
        level0_accounts = BudgetAccount.search(
            [("code", "in", EXPENSE_LEVEL0_CODES)], order="code"
        )
        if not level0_accounts:
            return []

        # Map every descendant account_id → its level0 parent
        level0_map = {}
        for l0 in level0_accounts:
            for desc in BudgetAccount.search(
                [("parent_path", "=like", f"{l0.parent_path}%")]
            ):
                level0_map[desc.id] = l0

        # Map every descendant account_id → its level1 parent
        level1_accounts = BudgetAccount.search(
            [("parent_id", "in", level0_accounts.ids)], order="code"
        )
        level1_map = {}
        for l1 in level1_accounts:
            for desc in BudgetAccount.search(
                [("parent_path", "=like", f"{l1.parent_path}%")]
            ):
                level1_map[desc.id] = l1

        # --- Build activity plan mapping ---
        activity_06 = self.env.ref(
            "account_analytic_kmitl.activity_06", raise_if_not_found=False
        )
        activity_09 = self.env.ref(
            "account_analytic_kmitl.activity_09", raise_if_not_found=False
        )
        allowed_parents = activity_06 | activity_09
        plan_activities = Analytic.search(
            [("parent_id", "in", allowed_parents.ids)], order="code"
        )

        # Map activity_id → its plan-level ancestor
        plan_activity_map = {}
        for plan in plan_activities:
            for desc in Analytic.search(
                [("parent_path", "=like", f"{plan.parent_path}%")]
            ):
                plan_activity_map[desc.id] = plan

        # --- Aggregate lines into hierarchy ---
        # {l0_id: {l1_id: {activity_id: {fund_id: amount}}}}
        data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))

        for line in lines:
            l0 = level0_map.get(line.account_id.id)
            l1 = level1_map.get(line.account_id.id)
            if not l0 or not l1:
                continue

            plan_act = plan_activity_map.get(line.activity_analytic_id.id)
            act_id = plan_act.id if plan_act else 0
            fund_id = line.fund_analytic_id.id or 0

            data[l0.id][l1.id][act_id][fund_id] += line.balance

        # --- Build flat row list ---
        rows = []
        l0_order = {code: i for i, code in enumerate(EXPENSE_LEVEL0_CODES)}
        sorted_l0 = sorted(
            (l0 for l0 in level0_accounts if l0.id in data),
            key=lambda a: l0_order.get(a.code, 99),
        )

        plan_act_by_id = {a.id: a for a in plan_activities}
        fund_cache = {}

        def get_fund(fund_id):
            if fund_id not in fund_cache:
                fund_cache[fund_id] = Analytic.browse(fund_id)
            return fund_cache[fund_id]

        l0_num = 0
        for l0 in sorted_l0:
            l0_num += 1
            l0_data = data[l0.id]
            l0_total = sum(
                amt
                for l1d in l0_data.values()
                for actd in l1d.values()
                for amt in actd.values()
            )
            rows.append(
                {"level": 0, "prefix": f"{l0_num}.", "name": l0.name, "amount": l0_total}
            )

            sorted_l1 = sorted(
                (l1 for l1 in level1_accounts if l1.id in l0_data and l1.parent_id == l0),
                key=lambda a: a.code or "",
            )
            l1_num = 0
            for l1 in sorted_l1:
                l1_num += 1
                l1_data = l0_data[l1.id]
                l1_total = sum(
                    amt for actd in l1_data.values() for amt in actd.values()
                )
                rows.append(
                    {
                        "level": 1,
                        "prefix": f"{l0_num}.{l1_num}",
                        "name": l1.name,
                        "amount": l1_total,
                    }
                )

                # Level 2: activities (only those matching plan_activities)
                sorted_act_ids = sorted(
                    (aid for aid in l1_data if aid in plan_act_by_id),
                    key=lambda aid: plan_act_by_id[aid].code or "",
                )
                for act_id in sorted_act_ids:
                    act = plan_act_by_id[act_id]
                    act_data = l1_data[act_id]
                    act_total = sum(act_data.values())
                    rows.append(
                        {"level": 2, "prefix": "-", "name": act.name, "amount": act_total}
                    )

                    # Level 3: funds
                    sorted_fund_ids = sorted(
                        (fid for fid in act_data if fid),
                        key=lambda fid: get_fund(fid).code or "",
                    )
                    for fund_id in sorted_fund_ids:
                        fund = get_fund(fund_id)
                        rows.append(
                            {
                                "level": 3,
                                "prefix": ":",
                                "name": fund.name,
                                "amount": act_data[fund_id],
                            }
                        )

        return rows

    def action_open_f3_report(self):
        """Open F3 report in a new browser tab as HTML."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_summary/compilation/{self.id}/f3/html",
            "target": "new",
        }

    def action_print_f3_report(self):
        """Print F3 report as PDF."""
        self.ensure_one()
        return self.env.ref(
            "budget_appropriation_summary_f3.action_report_compilation_f3"
        ).report_action(self)

    def _get_book_section_templates(self):
        """Insert the F3-P section right after F23 in the per-unit book."""
        sections = super()._get_book_section_templates()
        f3_section = "budget_appropriation_summary_f3.report_compilation_book_f3_section"
        index = 0
        for position, tmpl in enumerate(sections):
            if tmpl.endswith("report_compilation_book_f23_section"):
                index = position + 1
                break
        sections.insert(index, f3_section)
        return sections
