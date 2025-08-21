import logging
from collections import defaultdict

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetAppropriationReport(models.TransientModel):
    _name = "budget.appropriation.report"
    _description = "Budget Appropriation Hierarchical Report"

    move_id = fields.Many2one("budget.move", string="Budget Move", required=True)

    @api.model
    def get_hierarchical_data(self, move_id, options=None):
        """Generate hierarchical data structure for budget appropriation preview"""
        if options is None:
            options = {}

        move = self.env["budget.move"].browse(move_id)

        if not move or move.move_type != 'appropriation':
            return {"error": "Invalid appropriation move"}

        # Get non-virtual lines only
        lines = move.line_ids

        # Build hierarchy: Activities → [Departments] → Funds → Budget Accounts → Lines
        # For F4 revenue, show only budget accounts hierarchy
        if options.get('accounts_only', False):
            hierarchy = self._build_accounts_only_hierarchy(lines)
        else:
            hierarchy = self._build_hierarchy(lines, hide_department=options.get('hide_department', False))

        # Calculate totals
        total_amount = sum(line.balance for line in lines)

        return {
            "move": {
                "id": move.id,
                "name": move.name,
                "date": move.date.strftime("%d/%m/%Y") if move.date else "",
                "state": move.state,
                "total_amount": total_amount,
                "currency_symbol": move.currency_id.symbol or "฿",
                "source_analytic_id": {
                    "id": move.source_analytic_id.id,
                    "name": move.source_analytic_id.name,
                    "code": move.source_analytic_id.code,
                } if move.source_analytic_id else None,
                "department_analytic_id": {
                    "id": move.department_analytic_id.id,
                    "name": move.department_analytic_id.name,
                    "code": move.department_analytic_id.code,
                    "complete_name": self._get_complete_name_without_codes(move.department_analytic_id),
                } if move.department_analytic_id else None,
                "journal_id": {
                    "id": move.journal_id.id,
                    "name": move.journal_id.name,
                    "code": move.journal_id.code if hasattr(move.journal_id, 'code') else '',
                } if move.journal_id else None,
                "date_range_fy_id": {
                    "id": move.date_range_fy_id.id,
                    "name": move.date_range_fy_id.name,
                    "display_name": move.date_range_fy_id.display_name,
                } if move.date_range_fy_id else None,
            },
            "hierarchy": hierarchy,
            "summary": {
                "total_lines": len(lines),
                "total_amount": total_amount,
                "activities_count": len(hierarchy),
            }
        }

    def _build_accounts_only_hierarchy(self, lines):
        """Build hierarchy showing only budget accounts structure"""
        # Group lines by budget account hierarchy
        account_groups = defaultdict(list)

        for line in lines:
            if line.account_id:
                # Use account code as key, but we'll build full hierarchy
                account_groups[line.account_id.id].append({
                    "id": line.id,
                    "account": {
                        "id": line.account_id.id,
                        "name": line.account_id.name,
                        "code": line.account_id.code,
                        "parent_path": line.account_id.parent_path or '',
                    },
                    "balance": line.balance,
                    "note": line.note or "",
                })

        # Get all account IDs including parents
        all_account_ids = set()
        for account_id, group_lines in account_groups.items():
            account = self.env['budget.account'].browse(account_id)
            if account.parent_path:
                path_ids = [int(id_str) for id_str in account.parent_path.strip('/').split('/') if id_str]
                all_account_ids.update(path_ids)
            else:
                all_account_ids.add(account_id)

        # Get all accounts for hierarchy building
        all_accounts = self.env['budget.account'].browse(list(all_account_ids))
        account_map = {acc.id: acc for acc in all_accounts}

        # Build tree structure
        root_nodes = {}

        for account_id, group_lines in account_groups.items():
            account = account_map.get(account_id)
            if not account:
                continue

            # Build path from root to this account
            path = []
            if account.parent_path:
                path_ids = [int(id_str) for id_str in account.parent_path.strip('/').split('/') if id_str]
                path = [account_map[pid] for pid in path_ids if pid in account_map]
            else:
                path = [account]

            # Navigate/create tree structure
            current_level = root_nodes
            for i, path_account in enumerate(path):
                node_key = f"account_{path_account.code}"

                if node_key not in current_level:
                    current_level[node_key] = {
                        "key": node_key,
                        "type": "account",
                        "level": i + 1,
                        "name": path_account.name,
                        "code": path_account.code,
                        "children": {},
                        "total_amount": 0,
                        "line_count": 0,
                        "line_details": [],
                    }

                # If this is the final account (has actual lines), add line details
                if i == len(path) - 1:
                    for line_data in group_lines:
                        current_level[node_key]["line_details"].append({
                            "id": line_data["id"],
                            "balance": line_data["balance"],
                            "note": line_data["note"],
                        })
                        current_level[node_key]["total_amount"] += line_data["balance"]
                        current_level[node_key]["line_count"] += 1

                current_level = current_level[node_key]["children"]

        # Convert to list and calculate totals
        return self._convert_dict_to_list_and_calculate_totals(root_nodes)

    def _build_hierarchy(self, lines, hide_department=False):
        """Build complete hierarchical structure using parent_path for full hierarchy"""
        # Collect all unique analytic accounts from the lines
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

        # Get complete hierarchy paths for all analytic accounts
        hierarchy_paths = self._get_complete_hierarchy_paths(all_analytic_ids)

        # Get complete hierarchy paths for budget accounts
        budget_account_paths = self._get_budget_account_hierarchy_paths(all_budget_account_ids)

        # Build line data with complete paths
        line_data_with_paths = []

        for line in lines:
            # Get the complete paths for this line's analytic accounts
            paths = {
                'activity': self._get_path_hierarchy(line.activity_analytic_id, hierarchy_paths) if line.activity_analytic_id else [],
                'department': self._get_path_hierarchy(line.department_analytic_id, hierarchy_paths) if line.department_analytic_id else [],
                'fund': self._get_path_hierarchy(line.fund_analytic_id, hierarchy_paths) if line.fund_analytic_id else [],
            }

            # Get budget account hierarchy path
            budget_account_path = []
            if line.account_id and line.account_id.id in budget_account_paths:
                if line.account_id.parent_path:
                    path_ids = [int(id_str) for id_str in line.account_id.parent_path.strip('/').split('/') if id_str]
                    for account_id in path_ids:
                        if account_id in budget_account_paths:
                            budget_account_path.append(budget_account_paths[account_id])
                else:
                    budget_account_path.append(budget_account_paths[line.account_id.id])

            line_data = {
                "id": line.id,
                "account": {
                    "id": line.account_id.id,
                    "name": line.account_id.name,
                    "code": line.account_id.code,
                },
                "budget_account_path": budget_account_path,
                "balance": line.balance,
                "note": line.note or "",
                "analytic_distribution": line.analytic_distribution or {},
                "paths": paths
            }

            line_data_with_paths.append(line_data)

        # Build the hierarchy tree from the paths
        return self._build_tree_from_paths(line_data_with_paths, hide_department=hide_department)

    def _get_analytic_info(self, line, field_name):
        """Extract analytic account information"""
        analytic_account = getattr(line, field_name, None)
        if not analytic_account:
            return None

        return {
            "id": analytic_account.id,
            "name": analytic_account.name,
            "code": analytic_account.code or "",
        }

    def _get_complete_name_without_codes(self, analytic_account):
        """Get complete hierarchy name without codes and slashes"""
        if not analytic_account:
            return ""

        # If account has parent_path, build hierarchy of names
        if analytic_account.parent_path:
            # Extract all IDs from parent_path
            path_ids = [int(id_str) for id_str in analytic_account.parent_path.strip('/').split('/') if id_str]

            # Get all parent accounts
            parent_accounts = self.env['account.analytic.account'].browse(path_ids)

            # Build the complete name from parent names (without codes)
            names = [acc.name for acc in parent_accounts if acc.name]

            # Join with space instead of slash
            return ' '.join(names)
        else:
            # No hierarchy, just return the name
            return analytic_account.name


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


    def _get_name_from_lines(self, lines, code, field_name):
        """Get the full name for a given code from lines"""
        for line in lines:
            analytic_account = getattr(line, field_name, None)
            if analytic_account and analytic_account.code == code:
                return analytic_account.name
        return code
