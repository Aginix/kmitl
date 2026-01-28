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
        presentation and budget overview reporting.

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
        Get F2 revenue data from linked revenue_appropriation_ids.

        Args:
            report_id: ID of budget.appropriation.report record

        Returns:
            dict: {
                "categories": [{"code", "name", "amount"}, ...],
                "summary": {"total_amount": float},
                "report": {"id", "name", "fiscal_year", "source"}
            }
        """
        report = self.env["budget.appropriation.report"].browse(report_id)

        if not report.exists():
            return {
                "categories": [],
                "summary": {"total_amount": 0},
                "report": None,
            }

        # Get revenue appropriation lines from linked appropriations
        lines = report.revenue_appropriation_ids.mapped("line_ids")

        # Build account_id -> total balance mapping
        account_totals = {}
        for line in lines:
            acc_id = line.account_id.id
            account_totals[acc_id] = account_totals.get(acc_id, 0) + line.balance

        # Aggregate by categories using parent_path hierarchy
        categories = []
        for code, name in self.REVENUE_CATEGORIES:
            account_ids = self._get_accounts_in_category(code)
            total = sum(account_totals.get(acc_id, 0) for acc_id in account_ids)
            categories.append({
                "code": code,
                "name": name,
                "amount": total,
            })

        # Calculate total and percentages
        total_amount = sum(c["amount"] for c in categories)
        for category in categories:
            if total_amount:
                category["percentage"] = round((category["amount"] / total_amount) * 100, 2)
            else:
                category["percentage"] = 0.0

        return {
            "categories": categories,
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
