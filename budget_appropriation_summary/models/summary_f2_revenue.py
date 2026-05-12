import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationSummaryF2Revenue(models.AbstractModel):
    """
    F2 Revenue Report for Master Summary.

    Aggregates revenue by parent categories across all compilations.
    Adapted from budget.appropriation.f2.revenue for master summary use.
    """

    _name = "budget.appropriation.summary.f2.revenue"
    _description = "Budget Appropriation Summary F2 Revenue Report"

    REVENUE_CATEGORIES = [
        ("43100 (ก)", "ค่าธรรมเนียมการศึกษา และค่าธรรมเนียมอื่น ๆ"),
        ("43300", "รายได้จากงานบริการ"),
        ("43400", "รายได้จากเงินผลประโยชน์"),
        ("43500", "รายได้จากการรับบริจาค หรือ เงินอุดหนุน"),
    ]

    @api.model
    def get_data(self, summary_id):
        """
        Get F2 revenue data from master summary with comparison.

        Args:
            summary_id: ID of budget.appropriation.master.summary record

        Returns:
            dict with categories, summary, report, compare_report
        """
        summary = self.env["budget.appropriation.master.summary"].browse(summary_id)

        if not summary.exists():
            return {
                "categories": [],
                "summary": {
                    "total_amount": 0,
                    "compare_total_amount": 0,
                    "diff_amount": 0,
                    "diff_percentage": 0,
                },
                "report": None,
                "compare_report": None,
            }

        category_totals = self._build_category_totals(summary)

        compare_summary = summary.compare_summary_id
        compare_totals = {}
        if compare_summary:
            compare_totals = self._build_category_totals(compare_summary)

        categories = []
        for code, name in self.REVENUE_CATEGORIES:
            amount = category_totals.get(code, 0)
            compare_amount = compare_totals.get(code, 0)
            diff_amount = amount - compare_amount
            categories.append(
                {
                    "code": code,
                    "name": name,
                    "amount": amount,
                    "compare_amount": compare_amount,
                    "diff_amount": diff_amount,
                    "diff_percentage": (
                        round((diff_amount / compare_amount) * 100, 2)
                        if compare_amount
                        else 0
                    ),
                }
            )

        total_amount = sum(c["amount"] for c in categories)
        compare_total_amount = sum(c["compare_amount"] for c in categories)

        for category in categories:
            category["percentage"] = (
                round((category["amount"] / total_amount) * 100, 2)
                if total_amount
                else 0.0
            )
            category["compare_percentage"] = (
                round(
                    (category["compare_amount"] / compare_total_amount) * 100, 2
                )
                if compare_total_amount
                else 0.0
            )

        diff_total = total_amount - compare_total_amount
        diff_total_percentage = (
            round((diff_total / compare_total_amount) * 100, 2)
            if compare_total_amount
            else 0
        )

        return {
            "categories": categories,
            "summary": {
                "total_amount": total_amount,
                "compare_total_amount": compare_total_amount,
                "diff_amount": diff_total,
                "diff_percentage": diff_total_percentage,
            },
            "report": {
                "id": summary.id,
                "name": summary.name,
                "fiscal_year": (
                    summary.account_fiscal_year_id.name
                    if summary.account_fiscal_year_id
                    else None
                ),
                "source": (
                    summary.source_analytic_id.name
                    if summary.source_analytic_id
                    else None
                ),
            },
            "compare_report": (
                {
                    "id": compare_summary.id,
                    "name": compare_summary.name,
                    "fiscal_year": (
                        compare_summary.account_fiscal_year_id.name
                        if compare_summary.account_fiscal_year_id
                        else None
                    ),
                    "source": (
                        compare_summary.source_analytic_id.name
                        if compare_summary.source_analytic_id
                        else None
                    ),
                }
                if compare_summary
                else None
            ),
        }

    def _build_category_totals(self, summary):
        """Build category_code -> balance mapping. Deduct lines are subtracted
        directly from "43100 (ก)" because revenue deduct lines do not specify
        activity/fund and cannot be classified by category."""
        appropriations = summary.revenue_appropriation_ids
        lines = appropriations.mapped("line_ids")

        account_totals = {}
        for line in lines:
            acc_id = line.account_id.id
            account_totals[acc_id] = account_totals.get(acc_id, 0) + line.balance

        totals = {}
        for code, _ in self.REVENUE_CATEGORIES:
            account_ids = self._get_accounts_in_category(code)
            totals[code] = sum(
                account_totals.get(acc_id, 0) for acc_id in account_ids
            )

        totals["43100 (ก)"] -= sum(
            appropriations.mapped("deduct_line_ids.balance")
        )

        return totals

    def _get_accounts_in_category(self, category_code):
        """Get all budget.account IDs in category hierarchy using parent_path."""
        parent = self.env["budget.account"].search(
            [
                ("code", "=", category_code),
                ("budget_type", "=", "revenue"),
            ],
            limit=1,
        )

        if not parent:
            _logger.warning(
                "Budget account with code '%s' not found", category_code
            )
            return []

        descendants = self.env["budget.account"].search(
            [
                ("parent_path", "like", f"{parent.parent_path}%"),
            ]
        )

        return descendants.ids
