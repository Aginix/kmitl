# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models


class BudgetAppropriationMasterSummary(models.Model):
    _inherit = "budget.appropriation.master.summary"

    def get_f24_report_data(self):
        """Prepare F24 report data grouped by department.

        Aggregates each `compilation_ids` entry by `department_analytic_id` and
        returns one row per department plus a grand-total row.
        """
        self.ensure_one()
        grouped = defaultdict(list)
        for comp in self.compilation_ids:
            grouped[comp.department_analytic_id].append(comp)

        def _row(dept, comps):
            reserve_15 = sum(c.code_0702000002 for c in comps)
            treasury = sum(c.treasury_replenishment_amount for c in comps)
            ma = sum(c.maintenance_amount for c in comps)
            # TODO: replace with real MA allocated % when upstream field exists
            ma_allocated_pct = 0.0
            recurrent = sum(c.recurrent_budget_amount for c in comps)
            capital = sum(c.capital_budget_amount for c in comps)
            # TODO: replace mock once external_funding_amount reflects real data
            external = 0.0
            total_1 = reserve_15 + treasury + ma + recurrent + capital + external
            edu = sum(c.education_total for c in comps)
            aca = sum(c.academic_total for c in comps)
            ind = sum(c.industrial_total for c in comps)
            soc = sum(c.social_total for c in comps)
            total_2 = edu + aca + ind + soc

            def _pct(x):
                return (x / total_2 * 100) if total_2 else 0.0

            edu_pct = _pct(edu)
            aca_pct = _pct(aca)
            ind_pct = _pct(ind)
            soc_pct = _pct(soc)
            return {
                "department_name": dept.name if dept else "",
                "department_code": dept.code if dept else "",
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

        sum_keys = (
            "reserve_15",
            "treasury",
            "ma",
            "recurrent",
            "capital",
            "external",
            "total_1",
            "education",
            "academic",
            "industrial",
            "social",
            "total_2",
            "total_1_2",
        )
        total = {k: sum(r[k] for r in rows) for k in sum_keys}
        total_2 = total["total_2"]

        def _pct(x):
            return (x / total_2 * 100) if total_2 else 0.0

        total.update(
            {
                "department_name": "รวม",
                "department_code": "",
                "ma_allocated_pct": 0.0,
                "education_pct": _pct(total["education"]),
                "academic_pct": _pct(total["academic"]),
                "industrial_pct": _pct(total["industrial"]),
                "social_pct": _pct(total["social"]),
            }
        )
        total["total_pct"] = (
            total["education_pct"]
            + total["academic_pct"]
            + total["industrial_pct"]
            + total["social_pct"]
        )

        return {
            "rows": rows,
            "total": total,
            "fiscal_year": self.account_fiscal_year_id.name or "",
        }

    def action_open_f24_report(self):
        return self._action_open_individual_report("f24")
