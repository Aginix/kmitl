# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationF4PRevenue(models.AbstractModel):
    """
    Budget Appropriation F4-P Revenue Report - Aggregate revenue by categories and departments.

    Business Purpose:
        Generates F4-P revenue report data by aggregating budget appropriation
        lines into predefined parent account categories, further broken down
        by top-level departments. Includes comparison with compare_report_id.

    Revenue Categories:
        - r49000: ค่าธรรมเนียมการศึกษา และค่าธรรมเนียมอื่น ๆ (includes 43100, 43200)
        - 43300: รายได้จากงานบริการ
        - 43400: รายได้จากเงินผลประโยชน์
        - 43500: รายได้จากการรับบริจาค หรือ เงินอุดหนุน
    """

    _name = "budget.appropriation.f4p.revenue"
    _description = "Budget Appropriation F4-P Revenue Report"

    REVENUE_CATEGORIES = [
        ("r49000", "ค่าธรรมเนียมการศึกษา และค่าธรรมเนียมอื่น ๆ"),
        ("43300", "รายได้จากงานบริการ"),
        ("43400", "รายได้จากเงินผลประโยชน์"),
        ("43500", "รายได้จากการรับบริจาค หรือ เงินอุดหนุน"),
    ]

    @api.model
    def get_data(self, report_id):
        """
        Get F4-P revenue data from linked revenue_appropriation_ids with comparison.

        Args:
            report_id: ID of budget.appropriation.report record

        Returns:
            dict: {
                "categories": [
                    {
                        "code": str,
                        "name": str,
                        "amount": float,
                        "compare_amount": float,
                        "diff_amount": float,
                        "diff_percentage": float,
                        "percentage": float,
                        "departments": [
                            {
                                "id", "code", "name", "amount", "percentage",
                                "compare_amount", "diff_amount", "diff_percentage"
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
        report = self.env["budget.appropriation.report"].browse(report_id)

        if not report.exists():
            return {
                "categories": [],
                "departments": [],
                "summary": {"total_amount": 0, "compare_total_amount": 0, "diff_amount": 0, "diff_percentage": 0},
                "report": None,
                "compare_report": None,
            }

        # Get top-level departments
        top_level_depts = self._get_top_level_departments()
        dept_map = {d.id: {"id": d.id, "code": d.code, "name": d.name} for d in top_level_depts}

        # Build current report totals: (category_code, dept_id) -> balance
        category_dept_totals = self._build_category_dept_totals(report, dept_map)

        # Build comparison totals if compare_report_id exists
        compare_report = report.compare_report_id
        compare_totals = {}
        if compare_report:
            compare_totals = self._build_category_dept_totals(compare_report, dept_map)

        # Aggregate by categories with comparison
        categories = []
        for code, name in self.REVENUE_CATEGORIES:
            # Sum by department within category
            dept_totals = {}
            compare_dept_totals = {}
            for dept_id in dept_map.keys():
                key = (code, dept_id)
                if key in category_dept_totals:
                    dept_totals[dept_id] = category_dept_totals[key]
                if key in compare_totals:
                    compare_dept_totals[dept_id] = compare_totals[key]

            category_total = sum(dept_totals.values())
            compare_category_total = sum(compare_dept_totals.values())

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
                "code": code,
                "name": name,
                "amount": category_total,
                "compare_amount": compare_category_total,
                "diff_amount": diff_cat_amount,
                "diff_percentage": diff_cat_percentage,
                "departments": sorted(departments, key=lambda x: x["code"]),
            })

        # Calculate category percentages
        total_amount = sum(c["amount"] for c in categories)
        compare_total_amount = sum(c["compare_amount"] for c in categories)
        for cat in categories:
            cat["percentage"] = round((cat["amount"] / total_amount) * 100, 2) if total_amount else 0

        # Summary with comparison
        diff_total = total_amount - compare_total_amount
        diff_total_percentage = round((diff_total / compare_total_amount) * 100, 2) if compare_total_amount else 0

        return {
            "categories": categories,
            "departments": sorted(dept_map.values(), key=lambda x: x["code"]),
            "summary": {
                "total_amount": total_amount,
                "compare_total_amount": compare_total_amount,
                "diff_amount": diff_total,
                "diff_percentage": diff_total_percentage,
            },
            "report": {
                "id": report.id,
                "name": report.name,
                "fiscal_year": report.account_fiscal_year_id.name if report.account_fiscal_year_id else None,
                "source": report.source_analytic_id.name if report.source_analytic_id else None,
            },
            "compare_report": {
                "id": compare_report.id,
                "name": compare_report.name,
                "fiscal_year": compare_report.account_fiscal_year_id.name if compare_report.account_fiscal_year_id else None,
                "source": compare_report.source_analytic_id.name if compare_report.source_analytic_id else None,
            } if compare_report else None,
        }

    def _build_category_dept_totals(self, report, dept_map):
        """
        Build (category_code, dept_id) -> balance mapping for a report.

        Args:
            report: budget.appropriation.report record
            dept_map: dict of dept_id -> dept_info

        Returns:
            dict: (category_code, dept_id) -> balance
        """
        lines = report.revenue_appropriation_ids.mapped("line_ids")

        # Build category code -> account_ids mapping
        category_accounts = {}
        for code, _ in self.REVENUE_CATEGORIES:
            category_accounts[code] = set(self._get_accounts_in_category(code))

        totals = {}
        for line in lines:
            acc_id = line.account_id.id
            top_dept_id = self._extract_top_level_dept_id(line.department_analytic_id)

            if top_dept_id and top_dept_id in dept_map:
                for code, _ in self.REVENUE_CATEGORIES:
                    if acc_id in category_accounts[code]:
                        key = (code, top_dept_id)
                        totals[key] = totals.get(key, 0) + line.balance
                        break

        return totals

    def _get_accounts_in_category(self, category_code):
        """
        Get all budget.account IDs in category hierarchy using parent_path.

        Args:
            category_code: Budget account code (e.g., "r49000", "43300")

        Returns:
            list: List of budget.account IDs in the category hierarchy
        """
        parent = self.env["budget.account"].search([
            ("code", "=", category_code),
            ("budget_type", "=", "revenue"),
        ], limit=1)

        if not parent:
            _logger.warning("Budget account with code '%s' not found", category_code)
            return []

        # Find parent and all descendants using parent_path LIKE
        descendants = self.env["budget.account"].search([
            ("parent_path", "like", f"{parent.parent_path}%"),
        ])

        return descendants.ids

    def _get_top_level_departments(self):
        """
        Get top-level departments (first level only).

        Returns:
            recordset: account.analytic.account records for top-level departments
        """
        return self.env["account.analytic.account"].search([
            ("plan_id.code", "=", "departments"),
            ("parent_id", "=", False),
        ], order="code ASC")

    def _extract_top_level_dept_id(self, department):
        """
        Extract top-level department ID from parent_path.

        parent_path format: "1/2/3/" where first element is the top-level ancestor.

        Args:
            department: account.analytic.account record

        Returns:
            int or None: Top-level department ID
        """
        if department and department.parent_path:
            try:
                return int(department.parent_path.split("/")[0])
            except (ValueError, IndexError):
                return None
        return None