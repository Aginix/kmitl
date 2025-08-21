import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationOverviewReport(models.TransientModel):
    _name = "budget.appropriation.overview.report"
    _description = "Budget Appropriation Overview Report"

    # Filter fields
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
    )
    department_ids = fields.Many2many(
        "account.analytic.account",
        "budget_overview_dept_rel",
        "report_id",
        "dept_id",
        string="Departments",
        domain="[('plan_id.code', '=', 'KTL_DEPARTMENT')]",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted"), ("all", "All")],
        string="State",
        default="all",
    )

    def _sort_key(self, node):
        custom_order = ['09', '06', '00']
        try:
            return custom_order.index(node.get('code', ''))
        except ValueError:
            return len(custom_order)

    @api.model
    def get_hierarchical_overview_data(self, filters):
        """Generate hierarchical data from multiple budget moves"""
        # Get filtered budget moves
        moves = self._get_filtered_moves(filters)

        if not moves:
            return {
                "filters": filters,
                "hierarchy": [],
                "summary": {
                    "total_amount": 0,
                    "move_count": 0,
                    "line_count": 0,
                    "fiscal_years": [],
                },
            }

        # Aggregate all non-virtual lines from these moves
        all_lines = self.env["budget.move.line"]
        for move in moves:
            all_lines |= move.line_ids

        # Build hierarchy using the existing logic from budget_appropriation_report
        hierarchy = self._build_aggregated_hierarchy(all_lines)
        hierarchy.sort(key=self._sort_key)
        # Get unique fiscal years
        fiscal_years = moves.mapped("date_range_fy_id")
        fiscal_year_names = ", ".join(fiscal_years.mapped("name"))

        return {
            "filters": filters,
            "hierarchy": hierarchy,
            "summary": {
                "total_amount": sum(line.balance for line in all_lines),
                "move_count": len(moves),
                "line_count": len(all_lines),
                "fiscal_years": fiscal_year_names,
            },
        }

    def _get_filtered_moves(self, filters):
        """Get budget moves based on filters"""
        domain = [("move_type", "=", "appropriation")]

        # State filter
        state_filter = filters.get("state", "all")
        if state_filter != "all":
            domain.append(("state", "=", state_filter))

        # Date filters
        if filters.get("date_from"):
            domain.append(("date", ">=", filters["date_from"]))
        if filters.get("date_to"):
            domain.append(("date", "<=", filters["date_to"]))

        # Fiscal year filter
        if filters.get("date_range_fy_id"):
            domain.append(("date_range_fy_id", "=", filters["date_range_fy_id"]))

        # Department filter with hierarchy support
        if filters.get("department_ids"):
            # Get all selected departments and their children
            all_dept_ids = self._get_departments_with_children(
                filters["department_ids"]
            )
            domain.append(("department_analytic_id", "in", all_dept_ids))

        return self.env["budget.move"].search(domain, order="date desc")

    def _build_aggregated_hierarchy(self, lines):
        """Build hierarchy with aggregated data from multiple moves"""
        # Reuse the existing hierarchy building logic
        report_model = self.env["budget.appropriation.report"]

        # Collect all unique analytic accounts and budget accounts
        all_analytic_ids = set()
        all_budget_account_ids = set()

        for line in lines:
            if line.activity_analytic_id:
                all_analytic_ids.add(line.activity_analytic_id.id)
            if line.department_analytic_id:
                all_analytic_ids.add(line.department_analytic_id.id)
            if line.fund_analytic_id:
                all_analytic_ids.add(line.fund_analytic_id.id)
            if line.account_id:
                all_budget_account_ids.add(line.account_id.id)

        # Get complete hierarchy paths
        hierarchy_paths = report_model._get_complete_hierarchy_paths(all_analytic_ids)
        budget_account_paths = report_model._get_budget_account_hierarchy_paths(
            all_budget_account_ids
        )

        # Build line data with paths
        line_data_with_paths = []

        for line in lines:
            paths = {
                "activity": (
                    report_model._get_path_hierarchy(
                        line.activity_analytic_id, hierarchy_paths
                    )
                    if line.activity_analytic_id
                    else []
                ),
                "department": (
                    report_model._get_path_hierarchy(
                        line.department_analytic_id, hierarchy_paths
                    )
                    if line.department_analytic_id
                    else []
                ),
                "fund": (
                    report_model._get_path_hierarchy(
                        line.fund_analytic_id, hierarchy_paths
                    )
                    if line.fund_analytic_id
                    else []
                ),
            }

            budget_account_path = []
            if line.account_id and line.account_id.id in budget_account_paths:
                if line.account_id.parent_path:
                    path_ids = [
                        int(id_str)
                        for id_str in line.account_id.parent_path.strip("/").split("/")
                        if id_str
                    ]
                    for account_id in path_ids:
                        if account_id in budget_account_paths:
                            budget_account_path.append(budget_account_paths[account_id])
                else:
                    budget_account_path.append(budget_account_paths[line.account_id.id])

            line_data = {
                "id": line.id,
                "move_id": line.move_id.id,
                "move_name": line.move_id.name,
                "account": {
                    "id": line.account_id.id,
                    "name": line.account_id.name,
                    "code": line.account_id.code,
                },
                "budget_account_path": budget_account_path,
                "balance": line.balance,
                "note": line.note or "",
                "analytic_distribution": line.analytic_distribution or {},
                "paths": paths,
            }

            line_data_with_paths.append(line_data)

        # Build the hierarchy tree
        return report_model._build_tree_from_paths(
            line_data_with_paths, hide_department=False
        )

    @api.model
    def get_filter_options(self):
        """Get available options for filters"""
        # Get fiscal years that have budget appropriations
        fiscal_years = self.env["account.fiscal.year"].search(
            [], order="date_from desc"
        )

        # Get departments that have budget data
        departments_with_data = self._get_departments_with_budget_data()

        # Build hierarchical structure
        dept_hierarchy = self._build_department_hierarchy(departments_with_data)

        return {
            "fiscal_years": [
                {
                    "id": fy.id,
                    "name": fy.name,
                    "date_start": fy.date_from.strftime("%Y-%m-%d"),
                    "date_end": fy.date_to.strftime("%Y-%m-%d"),
                }
                for fy in fiscal_years
            ],
            "departments": dept_hierarchy,
            "departments_flat": [
                {
                    "id": dept.id,
                    "name": dept.name,
                    "code": dept.code,
                    "complete_name": dept.complete_name,
                    "parent_id": dept.parent_id.id if dept.parent_id else None,
                }
                for dept in departments_with_data
            ],
            "states": [
                {"value": "draft", "label": "Draft"},
                {"value": "posted", "label": "Posted"},
                {"value": "all", "label": "All"},
            ],
        }

    def _build_department_hierarchy(self, departments):
        """Build hierarchical structure for departments"""
        dept_map = {}
        roots = []

        # Get departments that have direct budget data (not just as parents)
        direct_used_dept_ids = (
            self.env["budget.move"]
            .search(
                [
                    ("move_type", "=", "appropriation"),
                    ("department_analytic_id", "!=", False),
                ]
            )
            .mapped("department_analytic_id.id")
        )

        # First pass: create mapping
        for dept in departments:
            dept_data = {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "complete_name": dept.complete_name,
                "parent_id": dept.parent_id.id if dept.parent_id else None,
                "has_data": dept.id in direct_used_dept_ids,
                "children": [],
            }
            dept_map[dept.id] = dept_data

        # Second pass: build hierarchy
        for dept in departments:
            dept_data = dept_map[dept.id]
            if dept.parent_id and dept.parent_id.id in dept_map:
                dept_map[dept.parent_id.id]["children"].append(dept_data)
            else:
                roots.append(dept_data)

        return roots

    def _get_departments_with_children(self, department_ids):
        """Get department IDs including all their children"""
        if not department_ids:
            return []

        # Get all selected departments
        departments = self.env["account.analytic.account"].browse(department_ids)
        all_dept_ids = set(department_ids)

        # For each department, get all children
        for dept in departments:
            children = self.env["account.analytic.account"].search(
                [("id", "child_of", dept.id), ("plan_id.code", "=", "departments")]
            )
            all_dept_ids.update(children.ids)

        return list(all_dept_ids)

    def _get_departments_with_budget_data(self):
        """Get departments that have budget appropriation data"""
        # Get all departments used in budget appropriation moves
        used_dept_ids = (
            self.env["budget.move"]
            .search(
                [
                    ("move_type", "=", "appropriation"),
                    ("department_analytic_id", "!=", False),
                ]
            )
            .mapped("department_analytic_id.id")
        )

        if not used_dept_ids:
            return self.env["account.analytic.account"]

        # Get all parent departments of used departments
        all_dept_ids = set(used_dept_ids)
        used_departments = self.env["account.analytic.account"].browse(used_dept_ids)

        for dept in used_departments:
            # Add all parent departments to ensure hierarchy is complete
            parent = dept.parent_id
            while parent:
                if parent.plan_id.code == "departments":
                    all_dept_ids.add(parent.id)
                parent = parent.parent_id

        # Return all departments (used + their parents) ordered properly
        return (
            self.env["account.analytic.account"]
            .browse(list(all_dept_ids))
            .sorted(lambda d: (d.code or "", d.name))
        )
