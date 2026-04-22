import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationSummaryF11WExpense(models.AbstractModel):
    """
    Budget Appropriation Summary F11-W Expense Report - Pivot table by departments and funds.

    Business Purpose:
        Generates F11-W expense report as a pivot table showing expenses by:
        - Rows: Top-level departments
        - Columns: 10 Funds

    Columns:
        - 0100: กองทุนทั่วไป
        - 0200: กองทุนเพื่อการศึกษา
        - 0703: กองทุนพัฒนาบุคลากร
        - 0500: กองทุนกิจการนักศึกษา
        - 0400: กองทุนบริการวิชาการ
        - 0701: กองทุนทำนุบำรุงศิลปวัฒนธรรม
        - 0300: กองทุนวิจัย
        - 0600: กองทุนสินทรัพย์ถาวร
        - 0702: กองทุนสำรอง
        - 0705: กองทุนยุทธศาสตร์
    """

    _name = "budget.appropriation.summary.f11w.expense"
    _description = "Budget Appropriation Summary F11-W Expense Report (Pivot by Funds)"

    # Funds (xml_id, code, name) - ordered as requested
    FUNDS = [
        ("account_analytic_kmitl.fund_0100", "0100", "กองทุนทั่วไป"),
        ("account_analytic_kmitl.fund_0200", "0200", "กองทุนเพื่อการศึกษา"),
        ("account_analytic_kmitl.fund_0703", "0703", "กองทุนพัฒนาบุคลากร"),
        ("account_analytic_kmitl.fund_0500", "0500", "กองทุนกิจการนักศึกษา"),
        ("account_analytic_kmitl.fund_0400", "0400", "กองทุนบริการวิชาการ"),
        ("account_analytic_kmitl.fund_0701", "0701", "กองทุนทำนุบำรุงศิลปวัฒนธรรม"),
        ("account_analytic_kmitl.fund_0300", "0300", "กองทุนวิจัย"),
        ("account_analytic_kmitl.fund_0600", "0600", "กองทุนสินทรัพย์ถาวร"),
        ("account_analytic_kmitl.fund_0702", "0702", "กองทุนสำรอง"),
        ("account_analytic_kmitl.fund_0705", "0705", "กองทุนยุทธศาสตร์"),
    ]

    # All column codes in order
    COLUMN_CODES = ["0100", "0200", "0703", "0500", "0400", "0701", "0300", "0600", "0702", "0705"]

    @api.model
    def get_data(self, summary_id):
        """
        Get F11-W expense data as a pivot table.

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
                            "0100": {"amount", "compare_amount", "diff_amount", "diff_percentage"},
                            ...
                        },
                        "total": {"amount", "compare_amount", "diff_amount", "diff_percentage"}
                    },
                    ...
                ],
                "columns": [{"code", "name"}, ...],
                "column_totals": {"0100": {...}, ...},
                "summary": {"total_amount", "compare_total_amount", "diff_amount", "diff_percentage"},
                "report": {...},
                "compare_report": {...} or None
            }
        """
        summary = self.env["budget.appropriation.master.summary"].browse(summary_id)

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

        # Build fund path mapping
        fund_path_map = self._build_fund_path_map()

        # Build current report totals
        dept_column_totals = self._build_dept_column_totals(summary, dept_map, fund_path_map)

        # Build comparison totals if compare_summary_id exists
        compare_summary = summary.compare_summary_id
        compare_totals = {}
        if compare_summary:
            compare_totals = self._build_dept_column_totals(compare_summary, dept_map, fund_path_map)

        # Build pivot table data
        departments = []
        for dept_id in dept_map.keys():
            dept_info = dept_map[dept_id]
            columns = {}
            dept_total = 0
            compare_dept_total = 0

            # Process each column
            for column_code in self.COLUMN_CODES:
                key = (dept_id, column_code)
                amount = dept_column_totals.get(key, 0)
                compare_amount = compare_totals.get(key, 0)
                diff_amount = amount - compare_amount
                diff_percentage = round((diff_amount / compare_amount) * 100, 2) if compare_amount else 0

                columns[column_code] = {
                    "amount": amount,
                    "compare_amount": compare_amount,
                    "diff_amount": diff_amount,
                    "diff_percentage": diff_percentage,
                }
                dept_total += amount
                compare_dept_total += compare_amount

            # Include department if it has any data
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

        # Sort by department code
        departments = sorted(departments, key=lambda x: x["code"])

        # Calculate column totals
        column_totals = {}
        for column_code in self.COLUMN_CODES:
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

        # Build columns metadata
        columns_meta = []
        for xml_id, code, name in self.FUNDS:
            columns_meta.append({"code": code, "name": name})

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

    def _build_fund_path_map(self):
        """
        Build parent_path_prefix -> code mapping for funds.

        Returns:
            dict: path_prefix -> code
        """
        path_prefix_map = {}
        for xml_id, code, name in self.FUNDS:
            fund = self.env.ref(xml_id, raise_if_not_found=False)
            if fund:
                # Use the fund ID as the key for exact match and children
                path_prefix_map[fund.id] = code
            else:
                _logger.warning("Fund with xml_id '%s' not found", xml_id)
        return path_prefix_map

    def _build_dept_column_totals(self, summary, dept_map, fund_path_map):
        """
        Build (dept_id, column_code) -> balance mapping for a summary.

        Args:
            summary: budget.appropriation.master.summary record
            dept_map: dict of dept_id -> dept_info
            fund_path_map: dict of fund_id -> code

        Returns:
            dict: (dept_id, column_code) -> balance
        """
        totals = {}
        for compilation in summary.compilation_ids:
            top_dept_id = compilation.top_level_department_id()
            if not top_dept_id or top_dept_id not in dept_map:
                continue
            for line, sign in compilation.iter_signed_lines("expense"):
                fund = line.fund_analytic_id
                if not fund:
                    continue
                fund_code = self._get_fund_code(fund, fund_path_map)
                if fund_code:
                    key = (top_dept_id, fund_code)
                    totals[key] = totals.get(key, 0) + line.balance * sign

        return totals

    def _get_fund_code(self, fund, fund_path_map):
        """
        Get the fund code for a given fund record by checking parent_path.

        Args:
            fund: account.analytic.account record
            fund_path_map: dict of fund_id -> code

        Returns:
            str or None: Fund code if found
        """
        if not fund or not fund.parent_path:
            return None

        # Check exact match first
        if fund.id in fund_path_map:
            return fund_path_map[fund.id]

        # Check if any ancestor is in our funds list
        path_ids = fund.parent_path.strip("/").split("/")
        for path_id in path_ids:
            try:
                ancestor_id = int(path_id)
                if ancestor_id in fund_path_map:
                    return fund_path_map[ancestor_id]
            except (ValueError, TypeError):
                continue

        return None

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
