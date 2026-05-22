# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models
from odoo.tools.pdf import merge_pdf


# (key, type) — type drives template formatting: "money" / "pct".
# Keep ordering aligned with the table header.
F24_NUMERIC_COLUMNS = [
    ("reserve_15", "money"),
    ("treasury", "money"),
    ("ma", "money"),
    ("ma_allocated_pct", "pct"),
    ("recurrent", "money"),
    ("capital", "money"),
    ("external", "money"),
    ("total_1", "money"),
    ("education", "money"),
    ("education_pct", "pct"),
    ("academic", "money"),
    ("academic_pct", "pct"),
    ("industrial", "money"),
    ("industrial_pct", "pct"),
    ("social", "money"),
    ("social_pct", "pct"),
    ("total_2", "money"),
    ("total_pct", "pct"),
    ("total_1_2", "money"),
]


class BudgetAppropriationMasterSummary(models.Model):
    _inherit = "budget.appropriation.master.summary"

    def _get_merged_pdf(self):
        merged = super()._get_merged_pdf()
        report = self.env.ref(
            "budget_appropriation_summary_f24.action_report_compilation_f24"
        )
        f24_pdf, __ = report._render_qweb_pdf(report.id, self.ids)
        return merge_pdf([merged, f24_pdf])

    def get_f24_report_data(self):
        """Prepare F24 report data grouped by department.

        Aggregates each `compilation_ids` entry by `department_analytic_id` and
        returns one row per department plus a grand-total row.
        """
        self.ensure_one()
        config = self.env.ref(
            "budget_appropriation_summary_f24.f24_config_default",
            raise_if_not_found=False,
        )
        selected = config and config.department_analytic_ids
        selected_ids = set(selected.ids) if selected else set()
        # Expand selected parents to include their entire subtree, so compilations
        # tied to sub-departments roll up under the configured parent.
        subtree = (
            self.env["account.analytic.account"].search(
                [("id", "child_of", list(selected_ids))]
            )
            if selected_ids
            else None
        )
        subtree_ids = set(subtree.ids) if subtree else set()

        def _rollup_target(dept):
            """Highest ancestor of `dept` that is in the selected set (or dept itself)."""
            if not selected_ids:
                return dept
            for ancestor_id in (
                int(x) for x in (dept.parent_path or "").strip("/").split("/") if x
            ):
                if ancestor_id in selected_ids:
                    return self.env["account.analytic.account"].browse(ancestor_id)
            return dept  # unreachable when dept ∈ subtree

        grouped = defaultdict(list)
        for comp in self.compilation_ids:
            dept = comp.department_analytic_id
            if selected_ids and dept.id not in subtree_ids:
                continue
            grouped[_rollup_target(dept)].append(comp)

        def _row(dept, comps):
            # "สำรองจ่าย 15%" = deducted reserve codes 0702000002 + 0702000003;
            # compilation.deducted_reserve_amount already sums both.
            reserve_15 = sum(c.deducted_reserve_amount for c in comps)
            treasury = sum(c.treasury_replenishment_amount for c in comps)
            ma = sum(c.maintenance_amount for c in comps)
            # TODO: replace with real MA allocated % when upstream field exists.
            # Until then, 0.0 will render as '-' (same as a true 0 — flagged in PR).
            ma_allocated_pct = 0.0
            recurrent = sum(c.recurrent_budget_amount for c in comps)
            capital = sum(c.capital_budget_amount for c in comps)
            # TODO: replace mock once external_funding_amount has real data.
            external = 0.0
            total_1 = reserve_15 + treasury + ma + recurrent + capital + external
            edu = sum(c.education_total for c in comps)
            aca = sum(c.academic_total for c in comps)
            ind = sum(c.industrial_total for c in comps)
            soc = sum(c.social_total for c in comps)
            total_2 = edu + aca + ind + soc

            def _pct(x):
                return (x / total_2 * 100) if total_2 else 0.0

            edu_pct, aca_pct, ind_pct, soc_pct = (
                _pct(edu), _pct(aca), _pct(ind), _pct(soc),
            )
            return {
                "department_name": dept.name if dept else "",
                "reserve_15": reserve_15,
                "treasury": treasury,
                "ma": ma,
                "ma_allocated_pct": ma_allocated_pct,
                "recurrent": recurrent,
                "capital": capital,
                "external": external,
                "total_1": total_1,
                "education": edu,
                "education_pct": edu_pct,
                "academic": aca,
                "academic_pct": aca_pct,
                "industrial": ind,
                "industrial_pct": ind_pct,
                "social": soc,
                "social_pct": soc_pct,
                "total_2": total_2,
                "total_pct": edu_pct + aca_pct + ind_pct + soc_pct,
                "total_1_2": total_1 + total_2,
            }

        rows = [
            _row(dept, comps)
            for dept, comps in sorted(
                grouped.items(), key=lambda kv: kv[0].code or ""
            )
        ]

        money_keys = [k for k, t in F24_NUMERIC_COLUMNS if t == "money"]
        total = {k: sum(r[k] for r in rows) for k in money_keys}
        total_2 = total["total_2"]

        def _pct(x):
            return (x / total_2 * 100) if total_2 else 0.0

        total.update({
            "department_name": "รวม",
            "ma_allocated_pct": 0.0,
            "education_pct": _pct(total["education"]),
            "academic_pct": _pct(total["academic"]),
            "industrial_pct": _pct(total["industrial"]),
            "social_pct": _pct(total["social"]),
        })
        total["total_pct"] = (
            total["education_pct"]
            + total["academic_pct"]
            + total["industrial_pct"]
            + total["social_pct"]
        )

        columns = [{"key": k, "type": t} for k, t in F24_NUMERIC_COLUMNS]
        return {"columns": columns, "rows": rows, "total": total}

    def action_open_f24_report(self):
        return self._action_open_individual_report("f24")
