# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationF2Revenue(models.AbstractModel):
    """
    Budget Appropriation F2 Revenue Report - Aggregate revenue by parent categories.

    Business Purpose:
        Generates F2 revenue report data by aggregating budget appropriation
        lines into predefined parent account categories. Used for council
        presentation and budget overview reporting. Includes comparison with
        compare_report_id.

    Revenue Categories:
        - r49000: ค่าธรรมเนียมการศึกษา และค่าธรรมเนียมอื่น ๆ (includes 43100, 43200)
        - 43300: รายได้จากงานบริการ
        - 43400: รายได้จากเงินผลประโยชน์
        - 43500: รายได้จากการรับบริจาค หรือ เงินอุดหนุน
    """

    _name = "budget.appropriation.f2.revenue"
    _description = "Budget Appropriation F2 Revenue Report"

    REVENUE_CATEGORIES = [
        ("r49000", "ค่าธรรมเนียมการศึกษา และค่าธรรมเนียมอื่น ๆ"),
        ("43300", "รายได้จากงานบริการ"),
        ("43400", "รายได้จากเงินผลประโยชน์"),
        ("43500", "รายได้จากการรับบริจาค หรือ เงินอุดหนุน"),
    ]

    @api.model
    def get_data(self, report_id):
        """
        Get F2 revenue data from linked revenue_appropriation_ids with comparison.

        Args:
            report_id: ID of budget.appropriation.report record

        Returns:
            dict: {
                "categories": [
                    {
                        "code", "name", "amount", "percentage",
                        "compare_amount", "diff_amount", "diff_percentage"
                    },
                    ...
                ],
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
                "summary": {"total_amount": 0, "compare_total_amount": 0, "diff_amount": 0, "diff_percentage": 0},
                "report": None,
                "compare_report": None,
            }

        # Build current report totals: category_code -> balance
        category_totals = self._build_category_totals(report)

        # Build comparison totals if compare_report_id exists
        compare_report = report.compare_report_id
        compare_totals = {}
        if compare_report:
            compare_totals = self._build_category_totals(compare_report)

        # Aggregate by categories with comparison
        categories = []
        for code, name in self.REVENUE_CATEGORIES:
            amount = category_totals.get(code, 0)
            compare_amount = compare_totals.get(code, 0)
            diff_amount = amount - compare_amount
            diff_percentage = round((diff_amount / compare_amount) * 100, 2) if compare_amount else 0

            categories.append({
                "code": code,
                "name": name,
                "amount": amount,
                "compare_amount": compare_amount,
                "diff_amount": diff_amount,
                "diff_percentage": diff_percentage,
            })

        # Calculate total and percentages
        total_amount = sum(c["amount"] for c in categories)
        compare_total_amount = sum(c["compare_amount"] for c in categories)

        for category in categories:
            if total_amount:
                category["percentage"] = round((category["amount"] / total_amount) * 100, 2)
            else:
                category["percentage"] = 0.0

        # Summary with comparison
        diff_total = total_amount - compare_total_amount
        diff_total_percentage = round((diff_total / compare_total_amount) * 100, 2) if compare_total_amount else 0

        return {
            "categories": categories,
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

    def _build_category_totals(self, report):
        """
        Build category_code -> balance mapping for a report.

        Args:
            report: budget.appropriation.report record

        Returns:
            dict: category_code -> balance
        """
        lines = report.revenue_appropriation_ids.mapped("line_ids")

        # Build account_id -> total balance mapping
        account_totals = {}
        for line in lines:
            acc_id = line.account_id.id
            account_totals[acc_id] = account_totals.get(acc_id, 0) + line.balance

        # Aggregate by categories
        totals = {}
        for code, _ in self.REVENUE_CATEGORIES:
            account_ids = self._get_accounts_in_category(code)
            totals[code] = sum(account_totals.get(acc_id, 0) for acc_id in account_ids)

        return totals

    def _get_accounts_in_category(self, category_code):
        """
        Get all budget.account IDs in category hierarchy using parent_path.

        parent_path format: "1/2/3/" where numbers are account IDs.
        Example:
            - Account ID 10 has parent_path "10/"
            - Account ID 20 (child of 10) has parent_path "10/20/"
            - Account ID 30 (child of 20) has parent_path "10/20/30/"

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