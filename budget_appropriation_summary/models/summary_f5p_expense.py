import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationSummaryF5PExpense(models.AbstractModel):
    """
    Budget Appropriation Summary F5-P Expense Report - Aggregate expenses by type, category, and department.

    Business Purpose:
        Generates F5-P expense report data by aggregating budget appropriation
        lines into expense types, sub-categories, and top-level departments.
        Includes comparison with compare_summary_id.

    Structure (3 Levels):
        - Level 1: Expense Type (e.g., 51000 งบบุคลากร)
        - Level 2: Expense Category (e.g., ค่าจ้างชั่วคราว)
        - Level 3: Department (e.g., คณะวิทยาศาสตร์)
    """

    _name = "budget.appropriation.summary.f5p.expense"
    _description = "Budget Appropriation Summary F5-P Expense Report"

    # Expense types (Level 1)
    EXPENSE_TYPES = [
        ("51000", "งบบุคลากร"),
        ("52000", "งบดำเนินงาน"),
        ("53000", "งบลงทุน"),
        ("54000", "งบเงินอุดหนุน"),
        ("55000", "งบรายจ่ายอื่น"),
        ("07020", "กองทุนสำรอง"),
    ]

    # Sub-categories (Level 2) with account mapping
    # Format: (type_code, sub_name, mapping_type, codes)
    # mapping_type: "exact" for specific codes, "parent" for hierarchy lookup
    EXPENSE_CATEGORIES = [
        ("51000", "ค่าจ้างชั่วคราว", "exact", ["5101010003"]),
        ("51000", "ค่าจ้างลูกจ้างสัญญาจ้าง", "exact", ["5101010017"]),
        ("51000", "เงินประจำตำแหน่ง", "exact", ["5101010007", "5101010002", "5101010004", "5101010005", "5101010006"]),
        ("52000", "เงินค่าตอบแทน", "parent", ["52301"]),
        ("52000", "เงินค่าใช้สอย", "parent", ["52400"]),
        ("52000", "เงินค่าวัสดุ", "parent", ["52500"]),
        ("52000", "เงินค่าสาธารณูปโภค", "parent", ["52600"]),
        ("53000", "ค่าครุภัณฑ์", "parent", ["5412000000"]),
        ("53000", "ค่าที่ดินและสิ่งก่อสร้าง", "parent", ["5411000000"]),
        ("54000", "เงินอุดหนุนอื่น", "parent", ["54000"]),
        ("55000", "เงินรายจ่ายอื่นๆ", "parent", ["55000"]),
        ("07020", "กองทุนสำรอง", "exact", ["0702000001", "0702000002"]),
    ]

    @api.model
    def get_data(self, summary_id):
        """
        Get F5-P expense data from linked expense_appropriation_ids with comparison.

        Args:
            summary_id: ID of budget.appropriation.master.summary record

        Returns:
            dict: {
                "expense_types": [
                    {
                        "code": str,
                        "name": str,
                        "amount": float,
                        "percentage": float,
                        "compare_amount": float,
                        "compare_percentage": float,
                        "diff_amount": float,
                        "diff_percentage": float,
                        "categories": [
                            {
                                "name": str,
                                "amount": float,
                                "percentage": float,
                                "compare_amount": float,
                                "compare_percentage": float,
                                "diff_amount": float,
                                "diff_percentage": float,
                                "departments": [
                                    {"id", "code", "name", "amount", "percentage",
                                     "compare_amount", "diff_amount", "diff_percentage"},
                                    ...
                                ]
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
        summary = self.env["budget.appropriation.master.summary"].browse(summary_id)

        if not summary.exists():
            return {
                "expense_types": [],
                "departments": [],
                "summary": {"total_amount": 0, "compare_total_amount": 0, "diff_amount": 0, "diff_percentage": 0},
                "report": None,
                "compare_report": None,
            }

        # Get top-level departments
        top_level_depts = self._get_top_level_departments()
        dept_map = {d.id: {"id": d.id, "code": d.code, "name": d.name} for d in top_level_depts}

        # Build current report totals: (type_code, cat_name, dept_id) -> balance
        category_dept_totals = self._build_category_dept_totals(summary, dept_map)

        # Build comparison totals if compare_summary_id exists
        compare_summary = summary.compare_summary_id
        compare_totals = {}
        if compare_summary:
            compare_totals = self._build_category_dept_totals(compare_summary, dept_map)

        # Build expense types with categories and departments
        expense_types = []
        for type_code, type_name in self.EXPENSE_TYPES:
            # Get categories for this type
            type_categories = [
                (cat_name, mapping_type, codes)
                for t_code, cat_name, mapping_type, codes in self.EXPENSE_CATEGORIES
                if t_code == type_code
            ]

            categories = []
            type_total = 0
            compare_type_total = 0

            for cat_name, mapping_type, codes in type_categories:
                # Sum by department within category
                dept_totals = {}
                compare_dept_totals = {}

                for dept_id in dept_map.keys():
                    key = (type_code, cat_name, dept_id)
                    if key in category_dept_totals:
                        dept_totals[dept_id] = category_dept_totals[key]
                    if key in compare_totals:
                        compare_dept_totals[dept_id] = compare_totals[key]

                category_total = sum(dept_totals.values())
                compare_category_total = sum(compare_dept_totals.values())

                if category_total or compare_category_total:
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
                        "name": cat_name,
                        "amount": category_total,
                        "compare_amount": compare_category_total,
                        "diff_amount": diff_cat_amount,
                        "diff_percentage": diff_cat_percentage,
                        "departments": sorted(departments, key=lambda x: x["code"]),
                    })

                    type_total += category_total
                    compare_type_total += compare_category_total

            # Calculate category percentages
            for cat in categories:
                cat["percentage"] = round((cat["amount"] / type_total) * 100, 2) if type_total else 0
                cat["compare_percentage"] = round((cat["compare_amount"] / compare_type_total) * 100, 2) if compare_type_total else 0

            if type_total or compare_type_total:
                diff_type = type_total - compare_type_total
                diff_type_pct = round((diff_type / compare_type_total) * 100, 2) if compare_type_total else 0

                expense_types.append({
                    "code": type_code,
                    "name": type_name,
                    "amount": type_total,
                    "compare_amount": compare_type_total,
                    "diff_amount": diff_type,
                    "diff_percentage": diff_type_pct,
                    "categories": categories,
                })

        # Calculate type percentages
        total_amount = sum(t["amount"] for t in expense_types)
        compare_total_amount = sum(t["compare_amount"] for t in expense_types)
        for t in expense_types:
            t["percentage"] = round((t["amount"] / total_amount) * 100, 2) if total_amount else 0
            t["compare_percentage"] = round((t["compare_amount"] / compare_total_amount) * 100, 2) if compare_total_amount else 0

        # Summary with comparison
        diff_total = total_amount - compare_total_amount
        diff_total_pct = round((diff_total / compare_total_amount) * 100, 2) if compare_total_amount else 0

        return {
            "expense_types": expense_types,
            "departments": sorted(dept_map.values(), key=lambda x: x["code"]),
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

    def _build_category_dept_totals(self, summary, dept_map):
        """
        Build (type_code, cat_name, dept_id) -> balance mapping for a summary.

        Args:
            summary: budget.appropriation.master.summary record
            dept_map: dict of dept_id -> dept_info

        Returns:
            dict: (type_code, cat_name, dept_id) -> balance
        """
        # Pre-compute account_id -> (type_code, cat_name) mapping
        account_category_map = {}
        for type_code, cat_name, mapping_type, codes in self.EXPENSE_CATEGORIES:
            account_ids = self._get_accounts_for_category(mapping_type, codes)
            for acc_id in account_ids:
                account_category_map[acc_id] = (type_code, cat_name)

        # Iterate compilations so department attribution follows the
        # compilation (not the line) and deduct_line_ids are subtracted
        # — matching compilation.amount_expense_total (amount_net).
        totals = {}
        for compilation in summary.compilation_ids:
            top_dept_id = compilation.top_level_department_id()
            if not top_dept_id or top_dept_id not in dept_map:
                continue
            for line, sign in compilation.iter_signed_lines("expense"):
                acc_id = line.account_id.id
                if acc_id not in account_category_map:
                    continue
                type_code, cat_name = account_category_map[acc_id]
                key = (type_code, cat_name, top_dept_id)
                totals[key] = totals.get(key, 0) + line.balance * sign

        return totals

    def _get_accounts_for_category(self, mapping_type, codes):
        """
        Get budget.account IDs based on mapping type.

        Args:
            mapping_type: "exact" for specific codes, "parent" for hierarchy lookup
            codes: List of budget account codes

        Returns:
            list: List of budget.account IDs
        """
        account_ids = []

        for code in codes:
            if mapping_type == "exact":
                # Find exact account by code
                account = self.env["budget.account"].search([
                    ("code", "=", code),
                    ("budget_type", "=", "expense"),
                ], limit=1)
                if account:
                    account_ids.append(account.id)
                else:
                    _logger.warning("Budget account with code '%s' not found", code)
            else:  # parent
                # Find parent and all descendants
                parent = self.env["budget.account"].search([
                    ("code", "=", code),
                    ("budget_type", "=", "expense"),
                ], limit=1)
                if parent:
                    descendants = self.env["budget.account"].search([
                        ("parent_path", "like", f"{parent.parent_path}%"),
                    ])
                    account_ids.extend(descendants.ids)
                else:
                    _logger.warning("Budget account with code '%s' not found", code)

        return account_ids

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
