import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationSummaryF5WExpense(models.AbstractModel):
    """
    Budget Appropriation Summary F5-W Expense Report - Aggregate expenses by activity plans.

    Business Purpose:
        Generates F5-W expense report data by aggregating budget appropriation
        lines by activity plans (แผนงาน). Includes comparison with compare_summary_id.

    Activity Plans:
        - 06004: แผนงานวิจัย
        - 06005: แผนงานบูรณาการ
        - 06006: แผนงานยุทธศาสตร์
        - 09007: แผนงานจัดการศึกษาอุดมศึกษา
        - 09010: แผนงานบริการวิชาการแก่สังคม
        - 09011: แผนงานศาสนา ศิลปะ และวัฒนธรรม
    """

    _name = "budget.appropriation.summary.f5w.expense"
    _description = "Budget Appropriation Summary F5-W Expense Report"

    # Format: (xml_id, code, name)
    ACTIVITY_PLANS = [
        ("account_analytic_kmitl.activity_09007", "09007", "แผนงานจัดการศึกษาอุดมศึกษา"),
        ("account_analytic_kmitl.activity_09010", "09010", "แผนงานบริการวิชาการแก่สังคม"),
        ("account_analytic_kmitl.activity_09011", "09011", "แผนงานศาสนา ศิลปะ และวัฒนธรรม"),
        ("account_analytic_kmitl.activity_06004", "06004", "แผนงานวิจัย"),
        ("account_analytic_kmitl.activity_06005", "06005", "แผนงานบูรณาการ"),
        ("account_analytic_kmitl.activity_09006", "06006", "แผนงานยุทธศาสตร์"),
    ]

    @api.model
    def get_data(self, summary_id):
        """
        Get F5-W expense data from linked expense_appropriation_ids with comparison.

        Args:
            summary_id: ID of budget.appropriation.master.summary record

        Returns:
            dict: {
                "activities": [
                    {
                        "code": str,
                        "name": str,
                        "amount": float,
                        "percentage": float,
                        "compare_amount": float,
                        "compare_percentage": float,
                        "diff_amount": float,
                        "diff_percentage": float
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
        summary = self.env["budget.appropriation.master.summary"].browse(summary_id)

        if not summary.exists():
            return {
                "activities": [],
                "summary": {"total_amount": 0, "compare_total_amount": 0, "diff_amount": 0, "diff_percentage": 0},
                "report": None,
                "compare_report": None,
            }

        # Build current report totals
        activity_totals = self._build_activity_totals(summary)

        # Build comparison totals if compare_summary_id exists
        compare_summary = summary.compare_summary_id
        compare_totals = {}
        if compare_summary:
            compare_totals = self._build_activity_totals(compare_summary)

        # Build activities list with comparison (always show all plans)
        activities = []
        for xml_id, code, name in self.ACTIVITY_PLANS:
            amount = activity_totals.get(xml_id, 0)
            compare_amount = compare_totals.get(xml_id, 0)
            diff_amount = amount - compare_amount
            activities.append({
                "code": code,
                "name": name,
                "amount": amount,
                "compare_amount": compare_amount,
                "diff_amount": diff_amount,
                "diff_percentage": round((diff_amount / compare_amount) * 100, 2) if compare_amount else 0,
            })

        # Calculate percentages
        total_amount = sum(a["amount"] for a in activities)
        compare_total_amount = sum(a["compare_amount"] for a in activities)
        for act in activities:
            act["percentage"] = round((act["amount"] / total_amount) * 100, 2) if total_amount else 0
            act["compare_percentage"] = round((act["compare_amount"] / compare_total_amount) * 100, 2) if compare_total_amount else 0

        # Summary with comparison
        diff_total = total_amount - compare_total_amount
        diff_total_pct = round((diff_total / compare_total_amount) * 100, 2) if compare_total_amount else 0

        return {
            "activities": activities,
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

    def _build_activity_totals(self, summary):
        """
        Build xml_id -> balance mapping for a summary.

        Args:
            summary: budget.appropriation.master.summary record

        Returns:
            dict: xml_id -> balance
        """
        lines = summary.expense_appropriation_ids.mapped("line_ids")

        # Pre-compute parent_path_prefix -> xml_id mapping
        # Using parent_path prefix (e.g., "123/") to match all descendants
        path_prefix_map = {}
        for xml_id, code, name in self.ACTIVITY_PLANS:
            parent = self.env.ref(xml_id, raise_if_not_found=False)
            if parent:
                # parent_path starts with parent.id/ for all descendants
                path_prefix_map[f"{parent.id}/"] = xml_id
            else:
                _logger.warning("Activity plan with xml_id '%s' not found", xml_id)

        # Aggregate
        totals = {}
        for line in lines:
            activity = line.activity_analytic_id
            # Check which plan this activity belongs to
            for prefix, xml_id in path_prefix_map.items():
                if prefix in activity.parent_path or activity.parent_path.startswith(prefix):
                    totals[xml_id] = totals.get(xml_id, 0) + line.balance
                    break

        return totals
