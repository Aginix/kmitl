import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationSummaryF10WExpense(models.AbstractModel):
    """
    Budget Appropriation Summary F10-W Expense Report - Hierarchical by activity plans and expense types.

    Business Purpose:
        Generates F10-W expense report showing expenses by:
        - Rows: Hierarchical activity structure (ด้าน -> แผนงาน -> งาน -> กิจกรรม)
        - Columns: Expense types (งบบุคลากร, งบดําเนินงาน, etc.)

    Row Hierarchy (fetched dynamically from database):
        - Level 0: ด้าน (Dimension) - 2-digit codes (09, 06)
        - Level 1: แผนงาน (Plan) - 5-digit codes (09006, 09007)
        - Level 2: งานหลัก (Work) - 9-digit codes (090060601)
        - Level 3: งานรอง (Activity) - 11-digit codes (09007010110)

    Columns:
        - 51000: งบบุคลากร
        - 52000: งบดําเนินงาน
        - 54000: งบเงินอุดหนุน
        - 55000: งบรายจ่ายอื่น
        - 53000: งบลงทุน
        - 07020: กองทุนสํารอง
    """

    _name = "budget.appropriation.summary.f10w.expense"
    _description = "Budget Appropriation Summary F10-W Expense Report (Activity x Expense Type)"

    # Expense type columns (same as F5-P)
    EXPENSE_TYPES = [
        ("51000", "งบบุคลากร"),
        ("52000", "งบดําเนินงาน"),
        ("54000", "งบเงินอุดหนุน"),
        ("55000", "งบรายจ่ายอื่น"),
        ("53000", "งบลงทุน"),
        ("07020", "กองทุนสํารอง"),
    ]

    COLUMN_CODES = ["51000", "52000", "54000", "55000", "53000", "07020"]

    @api.model
    def get_data(self, summary_id):
        """
        Get F10-W expense data as flat row structure with levels.

        Args:
            summary_id: ID of budget.appropriation.master.summary record

        Returns:
            dict: {
                "rows": [{"level": 0-3, "name": str, "columns": {...}, "total": float}, ...],
                "columns": [...],
                "column_totals": {...},
                "summary": {...},
                "report": {...},
            }
        """
        summary = self.env["budget.appropriation.master.summary"].browse(summary_id)

        if not summary.exists():
            return self._empty_result()

        # Build expense type mapping (account_id -> expense_type_code)
        expense_type_map = self._build_expense_type_map()

        # Build activity totals: (activity_id, expense_type_code) -> balance
        activity_totals = self._build_activity_expense_totals(summary, expense_type_map)

        # Build flat row structure with levels (dynamic from database)
        rows = []
        grand_total = {code: 0 for code in self.COLUMN_CODES}

        for dimension in self._get_dimensions():
            dim_columns = {code: 0 for code in self.COLUMN_CODES}
            dim_total = 0
            dim_rows = []

            for plan_idx, plan in enumerate(self._get_plans(dimension)):
                plan_label = chr(ord('ก') + plan_idx)  # Thai: ก, ข, ค, ง...
                plan_columns = {code: 0 for code in self.COLUMN_CODES}
                plan_total = 0
                plan_rows = []

                for work_idx, work in enumerate(self._get_works(plan)):
                    work_label = str(work_idx + 1)  # 1, 2, 3...
                    work_columns = {code: 0 for code in self.COLUMN_CODES}
                    work_total = 0
                    work_rows = []

                    # Get child activities under this work
                    for activity in self._get_activities(work):
                        act_columns = {code: 0 for code in self.COLUMN_CODES}
                        act_total = 0

                        # Get amounts for this activity
                        for code in self.COLUMN_CODES:
                            key = (activity.id, code)
                            amount = activity_totals.get(key, 0)
                            act_columns[code] = amount
                            act_total += amount

                        if act_total:  # Only include if has data
                            work_rows.append({
                                "level": 3,
                                "name": f"- {activity.name}",
                                "columns": act_columns,
                                "total": act_total,
                            })

                            # Roll up to work level
                            for code in self.COLUMN_CODES:
                                work_columns[code] += act_columns[code]
                            work_total += act_total

                    if work_total:  # Only include if has data
                        plan_rows.append({
                            "level": 2,
                            "name": f"{work_label}. {work.name}",
                            "columns": work_columns,
                            "total": work_total,
                        })
                        plan_rows.extend(work_rows)

                        # Roll up to plan level
                        for code in self.COLUMN_CODES:
                            plan_columns[code] += work_columns[code]
                        plan_total += work_total

                if plan_total:  # Only include if has data
                    dim_rows.append({
                        "level": 1,
                        "name": f"{plan_label}. {plan.name}",
                        "columns": plan_columns,
                        "total": plan_total,
                    })
                    dim_rows.extend(plan_rows)

                    # Roll up to dimension level
                    for code in self.COLUMN_CODES:
                        dim_columns[code] += plan_columns[code]
                    dim_total += plan_total

            if dim_total:  # Only include if has data
                rows.append({
                    "level": 0,
                    "name": dimension.name,
                    "columns": dim_columns,
                    "total": dim_total,
                })
                rows.extend(dim_rows)

                # Roll up to grand total
                for code in self.COLUMN_CODES:
                    grand_total[code] += dim_columns[code]

        # Build column metadata
        columns_meta = [{"code": code, "name": name} for code, name in self.EXPENSE_TYPES]

        # Summary
        total_amount = sum(grand_total.values())

        return {
            "rows": rows,
            "columns": columns_meta,
            "column_totals": grand_total,
            "summary": {"total_amount": total_amount},
            "report": {
                "id": summary.id,
                "name": summary.name,
                "fiscal_year": summary.account_fiscal_year_id.name if summary.account_fiscal_year_id else None,
                "source": summary.source_analytic_id.name if summary.source_analytic_id else None,
            },
        }

    def _empty_result(self):
        """Return empty result structure."""
        return {
            "rows": [],
            "columns": [],
            "column_totals": {},
            "summary": {"total_amount": 0},
            "report": None,
        }

    def _get_dimensions(self):
        """
        Get dimension-level activities (top-level, 2-digit codes like 09, 06).

        Returns:
            recordset: account.analytic.account records
        """
        return self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "activities"),
            ("parent_id", "=", False),
        ], order="code DESC")

    def _get_plans(self, dimension):
        """
        Get plan-level activities under a dimension (5-digit codes).

        Args:
            dimension: account.analytic.account record (dimension level)

        Returns:
            recordset: account.analytic.account records
        """
        return self.env["account.analytic.account"].search([
            ("parent_id", "=", dimension.id),
        ], order="code ASC")

    def _get_works(self, plan):
        """
        Get work-level activities under a plan (9-digit codes).

        Args:
            plan: account.analytic.account record (plan level)

        Returns:
            recordset: account.analytic.account records
        """
        return self.env["account.analytic.account"].search([
            ("parent_id", "=", plan.id),
        ], order="code ASC")

    def _get_activities(self, work):
        """
        Get activity-level items under a work (11-digit codes).

        Args:
            work: account.analytic.account record (work level)

        Returns:
            recordset: account.analytic.account records
        """
        return self.env["account.analytic.account"].search([
            ("parent_id", "=", work.id),
        ], order="code ASC")

    def _build_expense_type_map(self):
        """
        Build account_id -> expense_type_code mapping.

        Returns:
            dict: budget.account ID -> expense type code
        """
        expense_type_map = {}

        for type_code, type_name in self.EXPENSE_TYPES:
            # Find parent account
            parent = self.env["budget.account"].search([
                ("code", "=", type_code),
                ("budget_type", "=", "expense"),
            ], limit=1)

            if parent:
                # Get all descendants
                descendants = self.env["budget.account"].search([
                    ("parent_path", "like", f"{parent.parent_path}%"),
                ])
                for acc in descendants:
                    expense_type_map[acc.id] = type_code
            else:
                _logger.warning("Budget account %s not found", type_code)

        return expense_type_map

    def _build_activity_expense_totals(self, summary, expense_type_map):
        """
        Build (activity_id, expense_type_code) -> balance mapping.

        Args:
            summary: budget.appropriation.master.summary record
            expense_type_map: dict of account_id -> expense_type_code

        Returns:
            dict: (activity_id, expense_type_code) -> balance
        """
        totals = {}
        for compilation in summary.compilation_ids:
            for line, sign in compilation.iter_signed_lines("expense"):
                activity = line.activity_analytic_id
                account_id = line.account_id.id

                if not activity or account_id not in expense_type_map:
                    continue

                expense_type_code = expense_type_map[account_id]
                key = (activity.id, expense_type_code)
                totals[key] = totals.get(key, 0) + line.balance * sign

        return totals
