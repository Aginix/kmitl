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
        ("53000", "งบลงทุน"),
        ("54000", "งบเงินอุดหนุน"),
        ("55000", "งบรายจ่ายอื่น"),
        ("07020", "กองทุนสํารอง"),
    ]

    COLUMN_CODES = ["51000", "52000", "54000", "55000", "53000", "07020"]

    @api.model
    def get_data(self, summary_id):
        """
        Get F10-W expense data as flat row structure with levels.

        Each level row's totals are computed by parent_path subtree matching,
        so a row aggregates every line whose activity sits anywhere beneath it
        — including sub-activities deeper than the displayed 4-level hierarchy.

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

        # Build (activity_parent_path, expense_type_code, balance) tuples so
        # any ancestor row can sum its full subtree via prefix matching.
        path_totals = self._build_activity_path_totals(summary, expense_type_map)

        # Build flat row structure with levels (dynamic from database)
        rows = []
        grand_total = {code: 0 for code in self.COLUMN_CODES}

        for dimension in self._get_dimensions():
            dim_columns = self._subtree_columns(path_totals, dimension.parent_path)
            dim_total = sum(dim_columns.values())

            if not dim_total:
                continue

            dim_rows = []

            for plan in self._get_plans(dimension):
                plan_columns = self._subtree_columns(path_totals, plan.parent_path)
                plan_total = sum(plan_columns.values())

                if not plan_total:
                    continue

                plan_rows = []

                for work in self._get_works(plan):
                    work_columns = self._subtree_columns(path_totals, work.parent_path)
                    work_total = sum(work_columns.values())

                    if not work_total:
                        continue

                    work_rows = []

                    for activity in self._get_activities(work):
                        act_columns = self._subtree_columns(path_totals, activity.parent_path)
                        act_total = sum(act_columns.values())

                        if not act_total:
                            continue

                        work_rows.append({
                            "level": 3,
                            "name": f"- {activity.name}",
                            "columns": act_columns,
                            "total": act_total,
                        })

                    plan_rows.append({
                        "level": 2,
                        "name": work.name,
                        "columns": work_columns,
                        "total": work_total,
                    })
                    plan_rows.extend(work_rows)

                dim_rows.append({
                    "level": 1,
                    "name": plan.name,
                    "columns": plan_columns,
                    "total": plan_total,
                })
                dim_rows.extend(plan_rows)

            rows.append({
                "level": 0,
                "name": dimension.name,
                "columns": dim_columns,
                "total": dim_total,
            })
            rows.extend(dim_rows)

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
        dimensions = self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "activities"),
            ("parent_id", "=", False),
        ])
        # Display order: codes starting with "09" first, then the rest by code ASC
        return dimensions.sorted(
            key=lambda d: (0 if (d.code or "").startswith("09") else 1, d.code or "")
        )

    def _get_plans(self, dimension):
        """
        Get direct plan-level children of a dimension (5-digit codes).

        Args:
            dimension: account.analytic.account record (dimension level)

        Returns:
            recordset: account.analytic.account records
        """
        plans = self._get_direct_children(dimension)
        # Display order: codes starting with "09" first, then the rest by code ASC
        return plans.sorted(
            key=lambda p: (0 if (p.code or "").startswith("09") else 1, p.code or "")
        )

    def _get_works(self, plan):
        """
        Get direct work-level children of a plan (9-digit codes).

        Args:
            plan: account.analytic.account record (plan level)

        Returns:
            recordset: account.analytic.account records
        """
        return self._get_direct_children(plan).sorted(key=lambda w: w.code or "")

    def _get_activities(self, work):
        """
        Get direct activity-level children of a work (11-digit codes).

        Sub-activities (14-digit and deeper) are not displayed as separate
        rows — their amounts roll up into the activity row's total via
        parent_path subtree matching in :meth:`_subtree_columns`.

        Args:
            work: account.analytic.account record (work level)

        Returns:
            recordset: account.analytic.account records
        """
        return self._get_direct_children(work).sorted(key=lambda a: a.code or "")

    def _get_direct_children(self, parent):
        """
        Return direct children of ``parent`` using parent_path matching.

        Direct children have parent_path == parent.parent_path + "<id>/", so
        their depth (slash count) is exactly one more than parent's.

        Args:
            parent: account.analytic.account record

        Returns:
            recordset: account.analytic.account records (direct children only)
        """
        if not parent.parent_path:
            return self.env["account.analytic.account"]
        parent_depth = parent.parent_path.count("/")
        candidates = self.env["account.analytic.account"].search([
            ("parent_path", "=like", f"{parent.parent_path}%"),
            ("id", "!=", parent.id),
        ])
        return candidates.filtered(
            lambda r: r.parent_path and r.parent_path.count("/") == parent_depth + 1
        )

    def _build_expense_type_map(self):
        """
        Build account_id -> expense_type_code mapping.

        Returns:
            dict: budget.account ID -> expense type code
        """
        expense_type_map = {}

        for type_code, _type_name in self.EXPENSE_TYPES:
            # Find parent account
            parent = self.env["budget.account"].search([
                ("code", "=", type_code),
                ("budget_type", "=", "expense"),
            ], limit=1)

            if parent:
                # Get all descendants (parent + subtree) via parent_path
                descendants = self.env["budget.account"].search([
                    ("parent_path", "=like", f"{parent.parent_path}%"),
                ])
                for acc in descendants:
                    expense_type_map[acc.id] = type_code
            else:
                _logger.warning("Budget account %s not found", type_code)

        return expense_type_map

    def _build_activity_path_totals(self, summary, expense_type_map):
        """
        Aggregate line balances keyed by the line's activity parent_path so
        any ancestor row can sum its subtree by prefix matching.

        Args:
            summary: budget.appropriation.master.summary record
            expense_type_map: dict of account_id -> expense_type_code

        Returns:
            list[tuple]: (activity_parent_path, expense_type_code, balance)
        """
        items = []
        for line in summary.expense_appropriation_ids.mapped("line_ids"):
            activity = line.activity_analytic_id
            if not activity or not activity.parent_path:
                continue
            code = expense_type_map.get(line.account_id.id)
            if not code:
                continue
            items.append((activity.parent_path, code, line.balance))
        return items

    def _subtree_columns(self, path_totals, parent_path):
        """
        Sum balances per expense-type column for every line whose activity
        parent_path is a descendant of (or equal to) ``parent_path``.

        Args:
            path_totals: list of (activity_parent_path, code, balance)
            parent_path: ancestor parent_path used as the prefix filter

        Returns:
            dict: code -> aggregated balance
        """
        columns = {code: 0 for code in self.COLUMN_CODES}
        if not parent_path:
            return columns
        for path, code, balance in path_totals:
            if path.startswith(parent_path):
                columns[code] += balance
        return columns
