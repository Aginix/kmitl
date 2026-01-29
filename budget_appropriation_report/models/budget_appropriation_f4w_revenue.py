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
        This is the inverse of F4-P report.

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
        Get F4-W revenue data from linked revenue_appropriation_ids.

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
                        "percentage": float,
                        "categories": [
                            {"code", "name", "amount", "percentage"},
                            ...
                        ]
                    },
                    ...
                ],
                "categories": [{"code", "name"}, ...],
                "summary": {"total_amount": float},
                "report": {"id", "name", "fiscal_year", "source"}
            }
        """
        report = self.env["budget.appropriation.report"].browse(report_id)

        if not report.exists():
            return {
                "departments": [],
                "categories": [],
                "summary": {"total_amount": 0},
                "report": None,
            }

        # Get revenue appropriation lines from linked appropriations
        lines = report.revenue_appropriation_ids.mapped("line_ids")

        # Get top-level departments
        top_level_depts = self._get_top_level_departments()
        dept_map = {d.id: {"id": d.id, "code": d.code, "name": d.name} for d in top_level_depts}

        # Build category code -> account_ids mapping
        category_accounts = {}
        for code, name in self.REVENUE_CATEGORIES:
            category_accounts[code] = set(self._get_accounts_in_category(code))

        # Build (top_dept_id, category_code) -> balance mapping
        dept_category_totals = {}
        for line in lines:
            acc_id = line.account_id.id
            top_dept_id = self._extract_top_level_dept_id(line.department_analytic_id)

            if top_dept_id and top_dept_id in dept_map:
                # Find which category this account belongs to
                for code, _ in self.REVENUE_CATEGORIES:
                    if acc_id in category_accounts[code]:
                        key = (top_dept_id, code)
                        dept_category_totals[key] = dept_category_totals.get(key, 0) + line.balance
                        break

        # Aggregate by departments
        departments = []
        for dept_id, dept_info in dept_map.items():
            # Sum by category within department
            category_totals = {}
            for code, name in self.REVENUE_CATEGORIES:
                key = (dept_id, code)
                if key in dept_category_totals:
                    category_totals[code] = dept_category_totals[key]

            dept_total = sum(category_totals.values())

            if dept_total:  # Only include departments with data
                # Build category list with percentages
                categories = []
                for code, name in self.REVENUE_CATEGORIES:
                    amount = category_totals.get(code, 0)
                    if amount:  # Only include non-zero
                        categories.append({
                            "code": code,
                            "name": name,
                            "amount": amount,
                            "percentage": round((amount / dept_total) * 100, 2) if dept_total else 0,
                        })

                departments.append({
                    **dept_info,
                    "amount": dept_total,
                    "categories": categories,
                })

        # Calculate department percentages
        total_amount = sum(d["amount"] for d in departments)
        for dept in departments:
            dept["percentage"] = round((dept["amount"] / total_amount) * 100, 2) if total_amount else 0

        # Sort departments by code
        departments = sorted(departments, key=lambda x: x["code"])

        return {
            "departments": departments,
            "categories": [{"code": c, "name": n} for c, n in self.REVENUE_CATEGORIES],
            "summary": {"total_amount": total_amount},
            "report": {
                "id": report.id,
                "name": report.name,
                "fiscal_year": report.account_fiscal_year_id.name if report.account_fiscal_year_id else None,
                "source": report.source_analytic_id.name if report.source_analytic_id else None,
            },
        }

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
