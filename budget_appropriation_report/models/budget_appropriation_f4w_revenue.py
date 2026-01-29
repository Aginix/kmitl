# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationF4WRevenue(models.AbstractModel):
    """
    Budget Appropriation F4-W Revenue Report - Aggregate revenue by departments then categories.

    Business Purpose:
        Generates F4-W revenue report data by aggregating budget appropriation
        lines by top-level departments first, then broken down by revenue categories.
        This is the inverse of F4-P report. Includes comparison with compare_report_id.

    Revenue Categories:
        - r49000: ค่าธรรมเนียมการศึกษา และค่าธรรมเนียมอื่น ๆ (includes 43100, 43200)
        - 43300: รายได้จากงานบริการ
        - 43400: รายได้จากเงินผลประโยชน์
        - 43500: รายได้จากการรับบริจาค หรือ เงินอุดหนุน
    """

    _name = "budget.appropriation.f4w.revenue"
    _description = "Budget Appropriation F4-W Revenue Report"

    REVENUE_CATEGORIES = [
        ("r49000", "ค่าธรรมเนียมการศึกษา และค่าธรรมเนียมอื่น ๆ"),
        ("43300", "รายได้จากงานบริการ"),
        ("43400", "รายได้จากเงินผลประโยชน์"),
        ("43500", "รายได้จากการรับบริจาค หรือ เงินอุดหนุน"),
    ]

    @api.model
    def get_data(self, report_id):
        """
        Get F4-W revenue data from linked revenue_appropriation_ids with comparison.

        Args:
            report_id: ID of budget.appropriation.report record

        Returns:
            dict: {
                "departments": [
                    {
                        "id": int,
                        "code": str,
                        "name": str,
                        "amount": float,
                        "compare_amount": float,
                        "diff_amount": float,
                        "diff_percentage": float,
                        "percentage": float,
                        "compare_percentage": float,
                        "categories": [
                            {
                                "code", "name", "amount", "percentage", "compare_percentage",
                                "compare_amount", "diff_amount", "diff_percentage"
                            },
                            ...
                        ]
                    },
                    ...
                ],
                "categories": [{"code", "name"}, ...],
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
                "departments": [],
                "categories": [],
                "summary": {"total_amount": 0, "compare_total_amount": 0, "diff_amount": 0, "diff_percentage": 0},
                "report": None,
                "compare_report": None,
            }

        # Get top-level departments
        top_level_depts = self._get_top_level_departments()
        dept_map = {d.id: {"id": d.id, "code": d.code, "name": d.name} for d in top_level_depts}

        # Build category code -> account_ids mapping
        category_accounts = {}
        for code, name in self.REVENUE_CATEGORIES:
            category_accounts[code] = set(self._get_accounts_in_category(code))

        # Build current report totals
        dept_category_totals = self._build_dept_category_totals(report, dept_map, category_accounts)

        # Build comparison totals if compare_report_id exists
        compare_report = report.compare_report_id
        compare_totals = {}
        if compare_report:
            compare_totals = self._build_dept_category_totals(compare_report, dept_map, category_accounts)

        # Aggregate by departments with comparison
        departments = []
        all_dept_ids = set(dept_map.keys())

        for dept_id in all_dept_ids:
            dept_info = dept_map[dept_id]

            # Sum by category within department
            category_totals = {}
            compare_category_totals = {}
            for code, name in self.REVENUE_CATEGORIES:
                key = (dept_id, code)
                if key in dept_category_totals:
                    category_totals[code] = dept_category_totals[key]
                if key in compare_totals:
                    compare_category_totals[code] = compare_totals[key]

            dept_total = sum(category_totals.values())
            compare_dept_total = sum(compare_category_totals.values())

            # Include department if it has data in either current or compare
            if dept_total or compare_dept_total:
                # Build category list with comparison
                categories = []
                for code, name in self.REVENUE_CATEGORIES:
                    amount = category_totals.get(code, 0)
                    compare_amount = compare_category_totals.get(code, 0)

                    # Include category if it has data in either current or compare
                    if amount or compare_amount:
                        diff_amount = amount - compare_amount
                        diff_percentage = round((diff_amount / compare_amount) * 100, 2) if compare_amount else 0

                        categories.append({
                            "code": code,
                            "name": name,
                            "amount": amount,
                            "compare_amount": compare_amount,
                            "diff_amount": diff_amount,
                            "diff_percentage": diff_percentage,
                            "percentage": round((amount / dept_total) * 100, 2) if dept_total else 0,
                            "compare_percentage": round((compare_amount / compare_dept_total) * 100, 2) if compare_dept_total else 0,
                        })

                diff_dept_amount = dept_total - compare_dept_total
                diff_dept_percentage = round((diff_dept_amount / compare_dept_total) * 100, 2) if compare_dept_total else 0

                departments.append({
                    **dept_info,
                    "amount": dept_total,
                    "compare_amount": compare_dept_total,
                    "diff_amount": diff_dept_amount,
                    "diff_percentage": diff_dept_percentage,
                    "categories": categories,
                })

        # Calculate department percentages
        total_amount = sum(d["amount"] for d in departments)
        compare_total_amount = sum(d["compare_amount"] for d in departments)
        for dept in departments:
            dept["percentage"] = round((dept["amount"] / total_amount) * 100, 2) if total_amount else 0
            dept["compare_percentage"] = round((dept["compare_amount"] / compare_total_amount) * 100, 2) if compare_total_amount else 0

        # Sort departments by code
        departments = sorted(departments, key=lambda x: x["code"])

        # Summary with comparison
        diff_total = total_amount - compare_total_amount
        diff_total_percentage = round((diff_total / compare_total_amount) * 100, 2) if compare_total_amount else 0

        return {
            "departments": departments,
            "categories": [{"code": c, "name": n} for c, n in self.REVENUE_CATEGORIES],
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

    def _build_dept_category_totals(self, report, dept_map, category_accounts):
        """
        Build (dept_id, category_code) -> balance mapping for a report.

        Args:
            report: budget.appropriation.report record
            dept_map: dict of dept_id -> dept_info
            category_accounts: dict of category_code -> set of account_ids

        Returns:
            dict: (dept_id, category_code) -> balance
        """
        lines = report.revenue_appropriation_ids.mapped("line_ids")
        totals = {}

        for line in lines:
            acc_id = line.account_id.id
            top_dept_id = self._extract_top_level_dept_id(line.department_analytic_id)

            if top_dept_id and top_dept_id in dept_map:
                for code, _ in self.REVENUE_CATEGORIES:
                    if acc_id in category_accounts[code]:
                        key = (top_dept_id, code)
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
            ("root_plan_id.code", "=", "departments"),
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