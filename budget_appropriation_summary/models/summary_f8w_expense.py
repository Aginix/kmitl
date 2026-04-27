import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationSummaryF8WExpense(models.AbstractModel):
    """
    Budget Appropriation Summary F8-W Expense Report - Aggregate expenses by departments then activity plans.

    Business Purpose:
        Generates F8-W expense report data by aggregating budget appropriation
        lines by top-level departments first, then broken down by activity plans.
        Includes comparison with compare_summary_id.

    Structure (2 Levels):
        - Level 1: Department (e.g., คณะวิศวกรรมศาสตร์)
        - Level 2: Activity Plan (e.g., 09007 แผนงานจัดการศึกษาอุดมศึกษา)

    Activity Plans:
        - 09007: แผนงานจัดการศึกษาอุดมศึกษา
        - 09010: แผนงานบริการวิชาการแก่สังคม
        - 09011: แผนงานศาสนา ศิลปและวัฒนธรรม
        - 06004: แผนงานวิจัย
    """

    _name = "budget.appropriation.summary.f8w.expense"
    _description = "Budget Appropriation Summary F8-W Expense Report"

    # Format: (xml_id, code, name)
    ACTIVITY_PLANS = [
        ("account_analytic_kmitl.activity_09007", "09007", "แผนงานจัดการศึกษาอุดมศึกษา"),
        ("account_analytic_kmitl.activity_09010", "09010", "แผนงานบริการวิชาการแก่สังคม"),
        ("account_analytic_kmitl.activity_09011", "09011", "แผนงานศาสนา ศิลปและวัฒนธรรม"),
        ("account_analytic_kmitl.activity_06004", "06004", "แผนงานวิจัย"),
    ]

    @api.model
    def get_data(self, summary_id):
        """
        Get F8-W expense data from linked expense_appropriation_ids with comparison.

        Args:
            summary_id: ID of budget.appropriation.master.summary record

        Returns:
            dict: {
                "departments": [
                    {
                        "id": int,
                        "code": str,
                        "name": str,
                        "amount": float,
                        "percentage": float,
                        "compare_amount": float,
                        "compare_percentage": float,
                        "diff_amount": float,
                        "diff_percentage": float,
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
                        ]
                    },
                    ...
                ],
                "activities": [{"code", "name"}, ...],
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
                "departments": [],
                "activities": [],
                "summary": {"total_amount": 0, "compare_total_amount": 0, "diff_amount": 0, "diff_percentage": 0},
                "report": None,
                "compare_report": None,
            }

        # Get top-level departments
        top_level_depts = self._get_top_level_departments()
        dept_map = {d.id: {"id": d.id, "code": d.code, "name": d.name} for d in top_level_depts}

        # Build activity plan path prefix mapping
        activity_path_map = self._build_activity_path_map()

        # Build current report totals: (dept_id, xml_id) -> balance
        dept_activity_totals = self._build_dept_activity_totals(summary, dept_map, activity_path_map)

        # Build comparison totals if compare_summary_id exists
        compare_summary = summary.compare_summary_id
        compare_totals = {}
        if compare_summary:
            compare_totals = self._build_dept_activity_totals(compare_summary, dept_map, activity_path_map)

        # Aggregate by departments with comparison
        departments = []
        all_dept_ids = set(dept_map.keys())

        for dept_id in all_dept_ids:
            dept_info = dept_map[dept_id]

            # Sum by activity within department
            activity_totals = {}
            compare_activity_totals = {}
            for xml_id, code, name in self.ACTIVITY_PLANS:
                key = (dept_id, xml_id)
                if key in dept_activity_totals:
                    activity_totals[xml_id] = dept_activity_totals[key]
                if key in compare_totals:
                    compare_activity_totals[xml_id] = compare_totals[key]

            dept_total = sum(activity_totals.values())
            compare_dept_total = sum(compare_activity_totals.values())

            # Include department if it has data in either current or compare
            if dept_total or compare_dept_total:
                # Build activity list with comparison (always show all plans)
                activities = []
                for xml_id, code, name in self.ACTIVITY_PLANS:
                    amount = activity_totals.get(xml_id, 0)
                    compare_amount = compare_activity_totals.get(xml_id, 0)

                    diff_amount = amount - compare_amount
                    diff_percentage = round((diff_amount / compare_amount) * 100, 2) if compare_amount else 0

                    activities.append({
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
                    "activities": activities,
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
            "activities": [{"code": c, "name": n} for _, c, n in self.ACTIVITY_PLANS],
            "summary": {
                "total_amount": total_amount,
                "compare_total_amount": compare_total_amount,
                "diff_amount": diff_total,
                "diff_percentage": diff_total_percentage,
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

    def _build_activity_path_map(self):
        """
        Build parent_path_prefix -> xml_id mapping for activity plans.

        Returns:
            dict: path_prefix -> xml_id
        """
        path_prefix_map = {}
        for xml_id, code, name in self.ACTIVITY_PLANS:
            parent = self.env.ref(xml_id, raise_if_not_found=False)
            if parent:
                path_prefix_map[f"{parent.id}/"] = xml_id
            else:
                _logger.warning("Activity plan with xml_id '%s' not found", xml_id)
        return path_prefix_map

    def _build_dept_activity_totals(self, summary, dept_map, activity_path_map):
        """
        Build (dept_id, xml_id) -> balance mapping for a summary.

        Args:
            summary: budget.appropriation.master.summary record
            dept_map: dict of dept_id -> dept_info
            activity_path_map: dict of path_prefix -> xml_id

        Returns:
            dict: (dept_id, xml_id) -> balance
        """
        totals = {}
        for compilation in summary.compilation_ids:
            top_dept_id = compilation.top_level_department_id()
            if not top_dept_id or top_dept_id not in dept_map:
                continue
            for line, sign in compilation.iter_signed_lines("expense"):
                activity = line.activity_analytic_id
                if not activity or not activity.parent_path:
                    continue
                for prefix, xml_id in activity_path_map.items():
                    if activity.parent_path.startswith(prefix):
                        key = (top_dept_id, xml_id)
                        totals[key] = totals.get(key, 0) + line.balance * sign
                        break

        return totals

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
