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
        hierarchy_paths = self._get_complete_hierarchy_paths(all_analytic_ids)
        budget_account_paths = self._get_budget_account_hierarchy_paths(
            all_budget_account_ids
        )

        # Build line data with paths
        line_data_with_paths = []

        for line in lines:
            paths = {
                "activity": (
                    self._get_path_hierarchy(
                        line.activity_analytic_id, hierarchy_paths
                    )
                    if line.activity_analytic_id
                    else []
                ),
                "department": (
                    self._get_path_hierarchy(
                        line.department_analytic_id, hierarchy_paths
                    )
                    if line.department_analytic_id
                    else []
                ),
                "fund": (
                    self._get_path_hierarchy(
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
        return self._build_tree_from_paths(
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

    def _get_complete_hierarchy_paths(self, analytic_ids):
        """Get complete hierarchy paths for analytic accounts using parent_path"""
        if not analytic_ids:
            return {}

        # Get all related analytic accounts (including parents) using parent_path
        analytic_accounts = self.env['account.analytic.account'].browse(list(analytic_ids))
        all_related_ids = set()

        for account in analytic_accounts:
            if account.parent_path:
                # Extract all IDs from parent_path (format: "1/2/3/")
                path_ids = [int(id_str) for id_str in account.parent_path.strip('/').split('/') if id_str]
                all_related_ids.update(path_ids)
            else:
                all_related_ids.add(account.id)

        # Fetch all related accounts with their hierarchy information
        all_accounts = self.env['account.analytic.account'].browse(list(all_related_ids))

        # Build hierarchy mapping
        hierarchy_map = {}
        for account in all_accounts:
            hierarchy_map[account.id] = {
                'id': account.id,
                'name': account.name,
                'code': account.code or '',
                'parent_id': account.parent_id.id if account.parent_id else None,
                'parent_path': account.parent_path or '',
                'root_plan_code': account.root_plan_id.code if account.root_plan_id else '',
                'level': len(account.parent_path.strip('/').split('/')) if account.parent_path else 1
            }

        return hierarchy_map

    def _get_budget_account_hierarchy_paths(self, account_ids):
        """Get complete hierarchy paths for budget accounts using parent_path"""
        if not account_ids:
            return {}

        # Get all related budget accounts (including parents) using parent_path
        budget_accounts = self.env['budget.account'].browse(list(account_ids))
        all_related_ids = set()

        for account in budget_accounts:
            if account.parent_path:
                # Extract all IDs from parent_path (format: "1/2/3/")
                path_ids = [int(id_str) for id_str in account.parent_path.strip('/').split('/') if id_str]
                all_related_ids.update(path_ids)
            else:
                all_related_ids.add(account.id)

        # Fetch all related accounts with their hierarchy information
        all_accounts = self.env['budget.account'].browse(list(all_related_ids))

        # Build hierarchy mapping
        hierarchy_map = {}
        for account in all_accounts:
            hierarchy_map[account.id] = {
                'id': account.id,
                'name': account.name,
                'code': account.code or '',
                'parent_id': account.parent_id.id if account.parent_id else None,
                'parent_path': account.parent_path or '',
                'level': len(account.parent_path.strip('/').split('/')) if account.parent_path else 1
            }

        return hierarchy_map

    def _get_path_hierarchy(self, analytic_account, hierarchy_map):
        """Get complete path hierarchy for a specific analytic account"""
        if not analytic_account or analytic_account.id not in hierarchy_map:
            return []

        path = []
        if analytic_account.parent_path:
            # Extract path IDs and build hierarchy
            path_ids = [int(id_str) for id_str in analytic_account.parent_path.strip('/').split('/') if id_str]
            for account_id in path_ids:
                if account_id in hierarchy_map:
                    path.append(hierarchy_map[account_id])
        else:
            # Single account without parents
            path.append(hierarchy_map[analytic_account.id])

        return path

    def _build_tree_from_paths(self, line_data_with_paths, hide_department=False):
        """Build tree structure from line data with complete paths"""
        from collections import defaultdict
        
        # Group lines by their complete paths
        tree_structure = {}

        for line_data in line_data_with_paths:
            # Create a unique path key combining all dimensions
            path_key = self._create_path_key(line_data['paths'], hide_department=hide_department)

            if path_key not in tree_structure:
                tree_structure[path_key] = {
                    'paths': line_data['paths'],
                    'lines': [],
                    'accounts': {}
                }

            # Group by account within the path
            account_key = line_data['account']['code']
            if account_key not in tree_structure[path_key]['accounts']:
                tree_structure[path_key]['accounts'][account_key] = {
                    'account': line_data['account'],
                    'lines': []
                }

            tree_structure[path_key]['accounts'][account_key]['lines'].append(line_data)

        # Convert to hierarchical structure
        return self._convert_to_hierarchy_tree(tree_structure, hide_department=hide_department)

    def _create_path_key(self, paths, hide_department=False):
        """Create a unique key from the complete paths"""
        key_parts = []

        # Activity path
        if paths.get('activity'):
            activity_codes = [acc['code'] for acc in paths['activity']]
            key_parts.append('A:' + '|'.join(activity_codes))

        # Department path (skip if hidden)
        if not hide_department and paths.get('department'):
            dept_codes = [acc['code'] for acc in paths['department']]
            key_parts.append('D:' + '|'.join(dept_codes))

        # Fund path
        if paths.get('fund'):
            fund_codes = [acc['code'] for acc in paths['fund']]
            key_parts.append('F:' + '|'.join(fund_codes))

        return '||'.join(key_parts)

    def _convert_to_hierarchy_tree(self, tree_structure, hide_department=False):
        """Convert grouped structure to hierarchical tree"""
        # Build a nested tree structure
        root_nodes = {}

        for path_key, path_data in tree_structure.items():
            paths = path_data['paths']

            # Start with activity hierarchy (root level)
            activity_path = paths.get('activity', [])
            if not activity_path:
                continue

            current_level = root_nodes

            # Build activity hierarchy
            for i, activity_node in enumerate(activity_path):
                node_key = f"activity_{activity_node['code']}"

                if node_key not in current_level:
                    current_level[node_key] = {
                        "key": node_key,
                        "type": "activity",
                        "level": i + 1,
                        "name": activity_node['name'],
                        "code": activity_node['code'],
                        "children": {},
                        "total_amount": 0,
                        "line_count": 0,
                        "expanded": False,
                    }

                current_level = current_level[node_key]["children"]

            # Add department hierarchy (skip if hidden)
            dept_path = paths.get('department', []) if not hide_department else []
            for i, dept_node in enumerate(dept_path):
                node_key = f"dept_{dept_node['code']}"

                if node_key not in current_level:
                    current_level[node_key] = {
                        "key": node_key,
                        "type": "department",
                        "level": len(activity_path) + i + 1,
                        "name": dept_node['name'],
                        "code": dept_node['code'],
                        "children": {},
                        "total_amount": 0,
                        "line_count": 0,
                        "expanded": False,
                    }

                current_level = current_level[node_key]["children"]

            # Add fund hierarchy
            fund_path = paths.get('fund', [])
            dept_levels = 0 if hide_department else len(dept_path)
            for i, fund_node in enumerate(fund_path):
                node_key = f"fund_{fund_node['code']}"

                if node_key not in current_level:
                    current_level[node_key] = {
                        "key": node_key,
                        "type": "fund",
                        "level": len(activity_path) + dept_levels + i + 1,
                        "name": fund_node['name'],
                        "code": fund_node['code'],
                        "children": {},
                        "total_amount": 0,
                        "line_count": 0,
                        "expanded": False,
                    }

                current_level = current_level[node_key]["children"]

            # Add budget account hierarchy and lines
            for account_key, account_data in path_data['accounts'].items():
                # Process each line under this account
                for line in account_data['lines']:
                    # Build budget account hierarchy
                    account_level = current_level
                    budget_account_path = line.get('budget_account_path', [])

                    # Create hierarchy for budget accounts
                    base_level = len(activity_path) + dept_levels + len(fund_path)
                    for j, account_node in enumerate(budget_account_path):
                        account_node_key = f"account_{account_node['code']}"

                        if account_node_key not in account_level:
                            account_level[account_node_key] = {
                                "key": account_node_key,
                                "type": "account",
                                "level": base_level + j + 1,
                                "name": account_node['name'],
                                "code": account_node['code'],
                                "children": {},
                                "total_amount": 0,
                                "line_count": 0,
                                "expanded": False,
                            }

                        # If this is the last account in hierarchy and it matches our line's account,
                        # add the line data to it
                        if j == len(budget_account_path) - 1 and account_node['id'] == line['account']['id']:
                            # Add line details to the final account node
                            if 'line_details' not in account_level[account_node_key]:
                                account_level[account_node_key]['line_details'] = []
                            account_level[account_node_key]['line_details'].append({
                                "id": line['id'],
                                "balance": line['balance'],
                                "note": line['note'],
                                "move_id": line.get('move_id'),
                                "move_name": line.get('move_name'),
                            })
                            # Update amount for this specific line
                            account_level[account_node_key]['total_amount'] += line['balance']
                            account_level[account_node_key]['line_count'] += 1

                        account_level = account_level[account_node_key]["children"]

        # Convert to list format and calculate totals
        return self._convert_dict_to_list_and_calculate_totals(root_nodes)

    def _convert_dict_to_list_and_calculate_totals(self, nodes_dict):
        """Convert dictionary structure to list and calculate totals"""
        result = []

        for node_key, node_data in nodes_dict.items():
            # Convert children first
            if node_data["children"]:
                node_data["children"] = self._convert_dict_to_list_and_calculate_totals(node_data["children"])

                # Calculate totals from children
                children_total = sum(child["total_amount"] for child in node_data["children"])
                children_count = sum(child["line_count"] for child in node_data["children"])

                # For nodes with their own amounts (like account nodes with line_details),
                # we keep their amounts and add children amounts
                # For other nodes, we only use children amounts
                if node_data.get("line_details"):
                    # This node has its own line details, add children totals to existing
                    node_data["total_amount"] += children_total
                    node_data["line_count"] += children_count
                else:
                    # This node doesn't have its own lines, use only children totals
                    node_data["total_amount"] = children_total
                    node_data["line_count"] = children_count

            # Remove the children key if it's empty and convert to list
            if isinstance(node_data["children"], dict) and not node_data["children"]:
                node_data["children"] = []

            result.append(node_data)

        return result
