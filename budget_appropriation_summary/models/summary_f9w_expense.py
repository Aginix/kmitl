import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationSummaryF9WExpense(models.AbstractModel):
    """
    Budget Appropriation Summary F9-W Expense Report - Pivot table by departments and activity plans.

    Business Purpose:
        Generates F9-W expense report as a pivot table showing expenses by:
        - Rows: Top-level departments
        - Columns: Activity Plans

    Columns:
        - 09007: แผนงานจัดการศึกษาอุดมศึกษา
        - 09010: แผนงานบริการวิชาการแก่สังคม
        - 09011: แผนงานศาสนา ศิลปและวัฒนธรรม
        - 06004: แผนงานวิจัย
        - 06005: แผนงานบูรณาการ
        - 06006: แผนงานยุทธศาสตร์
    """

    _name = "budget.appropriation.summary.f9w.expense"
    _description = "Budget Appropriation Summary F9-W Expense Report (Pivot)"

    # Activity plans (xml_id, code, name)
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
        Get F9-W expense data as a pivot table.

        Args:
            summary_id: ID of budget.appropriation.master.summary record

        Returns:
            dict: {
                "departments": [
                    {
                        "id": int,
                        "code": str,
                        "name": str,
                        "columns": {
                            "09007": {"amount", "compare_amount", "diff_amount", "diff_percentage"},
                            ...
                        },
                        "total": {"amount", "compare_amount", "diff_amount", "diff_percentage"}
                    },
                    ...
                ],
                "columns": [{"code", "name"}, ...],
                "column_totals": {"09007": {...}, ...},
                "summary": {"total_amount", "compare_total_amount", "diff_amount", "diff_percentage"},
                "report": {...},
                "compare_report": {...} or None
            }
        """
        summary = self.env["budget.appropriation.master.summary"].browse(summary_id)
        column_codes = [code for _xml_id, code, _name in self.ACTIVITY_PLANS]

        if not summary.exists():
            return {
                "departments": [],
                "columns": [],
                "column_totals": {},
                "summary": {"total_amount": 0, "compare_total_amount": 0, "diff_amount": 0, "diff_percentage": 0},
                "report": None,
                "compare_report": None,
            }

        # Get top-level departments
        top_level_depts = self._get_top_level_departments()
        dept_map = {d.id: {"id": d.id, "code": d.code, "name": d.name} for d in top_level_depts}

        # Build activity plan parent_path -> code mapping (includes the plan itself + all descendants)
        activity_path_map = self._build_activity_path_map()

        # Build current and comparison totals
        dept_column_totals = self._build_dept_column_totals(summary, dept_map, activity_path_map)
        compare_summary = summary.compare_summary_id
        compare_totals = self._build_dept_column_totals(compare_summary, dept_map, activity_path_map) if compare_summary else {}

        # Build pivot table data
        departments = []
        for dept_id, dept_info in dept_map.items():
            columns = {}
            dept_total = 0
            compare_dept_total = 0

            for column_code in column_codes:
                key = (dept_id, column_code)
                amount = dept_column_totals.get(key, 0)
                compare_amount = compare_totals.get(key, 0)
                diff_amount = amount - compare_amount

                columns[column_code] = {
                    "amount": amount,
                    "compare_amount": compare_amount,
                    "diff_amount": diff_amount,
                    "diff_percentage": round((diff_amount / compare_amount) * 100, 2) if compare_amount else 0,
                }
                dept_total += amount
                compare_dept_total += compare_amount

            if dept_total or compare_dept_total:
                diff_dept = dept_total - compare_dept_total
                departments.append({
                    **dept_info,
                    "columns": columns,
                    "total": {
                        "amount": dept_total,
                        "compare_amount": compare_dept_total,
                        "diff_amount": diff_dept,
                        "diff_percentage": round((diff_dept / compare_dept_total) * 100, 2) if compare_dept_total else 0,
                    },
                })

        departments.sort(key=lambda x: x["code"] or "")

        # Column totals
        column_totals = {}
        for column_code in column_codes:
            total = sum(d["columns"][column_code]["amount"] for d in departments)
            compare_total = sum(d["columns"][column_code]["compare_amount"] for d in departments)
            diff = total - compare_total
            column_totals[column_code] = {
                "amount": total,
                "compare_amount": compare_total,
                "diff_amount": diff,
                "diff_percentage": round((diff / compare_total) * 100, 2) if compare_total else 0,
            }

        # Summary
        total_amount = sum(d["total"]["amount"] for d in departments)
        compare_total_amount = sum(d["total"]["compare_amount"] for d in departments)
        diff_total = total_amount - compare_total_amount

        columns_meta = [{"code": code, "name": name} for _xml_id, code, name in self.ACTIVITY_PLANS]

        return {
            "departments": departments,
            "columns": columns_meta,
            "column_totals": column_totals,
            "summary": {
                "total_amount": total_amount,
                "compare_total_amount": compare_total_amount,
                "diff_amount": diff_total,
                "diff_percentage": round((diff_total / compare_total_amount) * 100, 2) if compare_total_amount else 0,
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
        Build parent_path -> code mapping for activity plans.

        Each key is the plan's own ``parent_path`` (already ends with "/"), so
        ``line.activity.parent_path.startswith(key)`` matches the plan itself
        and every descendant — and only those.

        Returns:
            dict: parent_path -> code
        """
        path_map = {}
        for xml_id, code, _name in self.ACTIVITY_PLANS:
            parent = self.env.ref(xml_id, raise_if_not_found=False)
            if parent and parent.parent_path:
                path_map[parent.parent_path] = code
            else:
                _logger.warning("Activity plan with xml_id '%s' not found", xml_id)
        return path_map

    def _build_dept_column_totals(self, summary, dept_map, activity_path_map):
        """
        Build (dept_id, column_code) -> balance mapping for a summary.

        Each line contributes to at most ONE column (the activity plan its
        ``activity_analytic_id`` belongs to), so balances cannot be
        double-counted across columns.

        Args:
            summary: budget.appropriation.master.summary record
            dept_map: dict of dept_id -> dept_info
            activity_path_map: dict of plan parent_path -> code

        Returns:
            dict: (dept_id, column_code) -> balance
        """
        totals = {}

        for line in summary.expense_appropriation_ids.mapped("line_ids"):
            top_dept_id = self._extract_top_level_dept_id(line.department_analytic_id)
            if not top_dept_id or top_dept_id not in dept_map:
                continue

            activity = line.activity_analytic_id
            if not activity or not activity.parent_path:
                continue

            for plan_path, code in activity_path_map.items():
                if activity.parent_path.startswith(plan_path):
                    key = (top_dept_id, code)
                    totals[key] = totals.get(key, 0) + line.balance
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
