import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationSummaryF5PExpense(models.AbstractModel):
    """
    Budget Appropriation Summary F5-P Expense Report - Aggregate expenses by type, category, and department.

    Business Purpose:
        Generates F5-P expense report data by aggregating budget appropriation
        lines into expense types, sub-categories, and top-level departments.
        Includes comparison with compare_summary_id.

    Structure (3 Levels):
        - Level 1: Expense Type (e.g., 51000 งบบุคลากร)
        - Level 2: Expense Category — direct children of the Level 1 budget.account
        - Level 3: Department (e.g., คณะวิทยาศาสตร์)
    """

    _name = "budget.appropriation.summary.f5p.expense"
    _description = "Budget Appropriation Summary F5-P Expense Report"

    # Expense types (Level 1)
    EXPENSE_TYPES = [
        ("51000", "งบบุคลากร"),
        ("52000", "งบดำเนินงาน"),
        ("53000", "งบลงทุน"),
        ("54000", "งบเงินอุดหนุน"),
        ("55000", "งบรายจ่ายอื่น"),
        ("07020", "กองทุนสำรอง"),
    ]

    @api.model
    def get_data(self, summary_id):
        """
        Get F5-P expense data from linked expense_appropriation_ids with comparison.

        Args:
            summary_id: ID of budget.appropriation.master.summary record

        Returns:
            dict: {
                "expense_types": [
                    {
                        "code": str,
                        "name": str,
                        "amount": float,
                        "percentage": float,
                        "compare_amount": float,
                        "compare_percentage": float,
                        "diff_amount": float,
                        "diff_percentage": float,
                        "categories": [
                            {
                                "name": str,
                                "amount": float,
                                "percentage": float,
                                "compare_amount": float,
                                "compare_percentage": float,
                                "diff_amount": float,
                                "diff_percentage": float,
                                "departments": [
                                    {"id", "code", "name", "amount", "percentage",
                                     "compare_amount", "diff_amount", "diff_percentage"},
                                    ...
                                ]
                            },
                            ...
                        ]
                    },
                    ...
                ],
                "departments": [{"id", "code", "name"}, ...],
                "summary": {
                    "total_amount": float,
                    "compare_total_amount": float,
                    "diff_amount": float,
                    "diff_percentage": float
                },
                "report": {"id", "name", "fiscal_year", "source"},
                "compare_report": {"id", "name", "fiscal_year", "source"} or None
            }
        """
        summary = self.env["budget.appropriation.master.summary"].browse(summary_id)

        if not summary.exists():
            return {
                "expense_types": [],
                "departments": [],
                "summary": {"total_amount": 0, "compare_total_amount": 0, "diff_amount": 0, "diff_percentage": 0},
                "report": None,
                "compare_report": None,
            }

        # Get top-level departments
        top_level_depts = self._get_top_level_departments()
        dept_map = {d.id: {"id": d.id, "code": d.code, "name": d.name} for d in top_level_depts}

        hierarchy = self._build_hierarchy()

        # Build current report totals: (type_code, cat_name, dept_id) -> balance
        category_dept_totals = self._build_category_dept_totals(summary, dept_map, hierarchy)

        # Build comparison totals if compare_summary_id exists
        compare_summary = summary.compare_summary_id
        compare_totals = {}
        if compare_summary:
            compare_totals = self._build_category_dept_totals(compare_summary, dept_map, hierarchy)

        # Build expense types with categories and departments
        expense_types = []
        for type_code, type_name in self.EXPENSE_TYPES:
            type_cat_names = [cat_name for cat_name, _path in hierarchy.get(type_code, [])]

            categories = []
            type_total = 0
            compare_type_total = 0

            for cat_name in type_cat_names:
                # Sum by department within category
                dept_totals = {}
                compare_dept_totals = {}

                for dept_id in dept_map.keys():
                    key = (type_code, cat_name, dept_id)
                    if key in category_dept_totals:
                        dept_totals[dept_id] = category_dept_totals[key]
                    if key in compare_totals:
                        compare_dept_totals[dept_id] = compare_totals[key]

                category_total = sum(dept_totals.values())
                compare_category_total = sum(compare_dept_totals.values())

                if category_total or compare_category_total:
                    # Build department list with comparison
                    departments = []
                    all_dept_ids = set(dept_totals.keys()) | set(compare_dept_totals.keys())

                    for dept_id in all_dept_ids:
                        amount = dept_totals.get(dept_id, 0)
                        compare_amount = compare_dept_totals.get(dept_id, 0)

                        if amount or compare_amount:
                            diff_amount = amount - compare_amount
                            diff_percentage = round((diff_amount / compare_amount) * 100, 2) if compare_amount else 0

                            departments.append({
                                **dept_map[dept_id],
                                "amount": amount,
                                "compare_amount": compare_amount,
                                "diff_amount": diff_amount,
                                "diff_percentage": diff_percentage,
                                "percentage": round((amount / category_total) * 100, 2) if category_total else 0,
                            })

                    # Category comparison
                    diff_cat_amount = category_total - compare_category_total
                    diff_cat_percentage = round((diff_cat_amount / compare_category_total) * 100, 2) if compare_category_total else 0

                    categories.append({
                        "name": cat_name,
                        "amount": category_total,
                        "compare_amount": compare_category_total,
                        "diff_amount": diff_cat_amount,
                        "diff_percentage": diff_cat_percentage,
                        "departments": sorted(departments, key=lambda x: x["code"]),
                    })

                    type_total += category_total
                    compare_type_total += compare_category_total

            # Calculate category percentages
            for cat in categories:
                cat["percentage"] = round((cat["amount"] / type_total) * 100, 2) if type_total else 0
                cat["compare_percentage"] = round((cat["compare_amount"] / compare_type_total) * 100, 2) if compare_type_total else 0

            if type_total or compare_type_total:
                diff_type = type_total - compare_type_total
                diff_type_pct = round((diff_type / compare_type_total) * 100, 2) if compare_type_total else 0

                expense_types.append({
                    "code": type_code,
                    "name": type_name,
                    "amount": type_total,
                    "compare_amount": compare_type_total,
                    "diff_amount": diff_type,
                    "diff_percentage": diff_type_pct,
                    "categories": categories,
                })

        # Calculate type percentages
        total_amount = sum(t["amount"] for t in expense_types)
        compare_total_amount = sum(t["compare_amount"] for t in expense_types)
        for t in expense_types:
            t["percentage"] = round((t["amount"] / total_amount) * 100, 2) if total_amount else 0
            t["compare_percentage"] = round((t["compare_amount"] / compare_total_amount) * 100, 2) if compare_total_amount else 0

        # Summary with comparison
        diff_total = total_amount - compare_total_amount
        diff_total_pct = round((diff_total / compare_total_amount) * 100, 2) if compare_total_amount else 0

        return {
            "expense_types": expense_types,
            "departments": sorted(dept_map.values(), key=lambda x: x["code"]),
            "summary": {
                "total_amount": total_amount,
                "compare_total_amount": compare_total_amount,
                "diff_amount": diff_total,
                "diff_percentage": diff_total_pct,
            },
            "report": {
                "id": summary.id,
                "name": summary.name,
                "fiscal_year": summary.account_fiscal_year_id.name if summary.account_fiscal_year_id else None,
                "source": summary.source_analytic_id.name if summary.source_analytic_id else None,
            },
            "compare_report": {
                "id": compare_summary.id,
                "name": compare_summary.name,
                "fiscal_year": compare_summary.account_fiscal_year_id.name if compare_summary.account_fiscal_year_id else None,
                "source": compare_summary.source_analytic_id.name if compare_summary.source_analytic_id else None,
            } if compare_summary else None,
        }

    def _build_hierarchy(self):
        """Resolve each EXPENSE_TYPES code to a budget.account record and return
        type_code -> [(cat_name, cat_parent_path), ...] from the parent's direct children."""
        hierarchy = {}
        for type_code, _type_name in self.EXPENSE_TYPES:
            parent = self.env["budget.account"].search([
                ("code", "=", type_code),
                ("budget_type", "=", "expense"),
            ], limit=1)
            if not parent:
                _logger.warning("Budget account with code '%s' not found", type_code)
                hierarchy[type_code] = []
                continue
            hierarchy[type_code] = [
                (child.name, child.parent_path)
                for child in parent.child_ids.sorted(key=lambda a: a.code)
            ]
        return hierarchy

    def _build_category_dept_totals(self, summary, dept_map, hierarchy):
        """Aggregate line balances by (type_code, cat_name, dept_id) using parent_path matching."""
        flat = [
            (t_code, cat_name, cat_path)
            for t_code, cats in hierarchy.items()
            for cat_name, cat_path in cats
        ]

        totals = {}
        for line in summary.expense_appropriation_ids.mapped("line_ids"):
            path = line.account_id.parent_path or ""
            top_dept_id = self._extract_top_level_dept_id(line.department_analytic_id)
            if not (top_dept_id and top_dept_id in dept_map):
                continue
            for type_code, cat_name, cat_path in flat:
                if path.startswith(cat_path):
                    key = (type_code, cat_name, top_dept_id)
                    totals[key] = totals.get(key, 0) + line.balance
                    break
        return totals

    def _get_top_level_departments(self):
        """Get top-level departments (first level only)."""
        return self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "departments"),
            ("parent_id", "=", False),
        ], order="code ASC")

    def _extract_top_level_dept_id(self, department):
        """Extract top-level department ID from parent_path."""
        if department and department.parent_path:
            try:
                return int(department.parent_path.split("/")[0])
            except (ValueError, IndexError):
                return None
        return None
