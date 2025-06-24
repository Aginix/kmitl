import logging
from collections import defaultdict

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetAppropriationReport(models.TransientModel):
    _name = "budget.appropriation.report"
    _description = "Budget Appropriation Hierarchical Report"

    move_id = fields.Many2one("budget.move", string="Budget Move", required=True)

    @api.model
    def get_hierarchical_data(self, move_id):
        """Generate hierarchical data structure for budget appropriation preview"""
        move = self.env["budget.move"].browse(move_id)
        
        if not move or move.move_type != 'appropriation':
            return {"error": "Invalid appropriation move"}
        
        # Get non-virtual lines only
        lines = move.line_ids.filtered(lambda l: not l.is_virtual_line)
        
        # Build hierarchy: Activities → Departments → Funds → Budget Accounts → Lines
        hierarchy = self._build_hierarchy(lines)
        
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
                "source_analytic": {
                    "id": move.source_analytic_id.id,
                    "name": move.source_analytic_id.name,
                    "code": move.source_analytic_id.code,
                } if move.source_analytic_id else None,
                "department_analytic": {
                    "id": move.department_analytic_id.id,
                    "name": move.department_analytic_id.name,
                    "code": move.department_analytic_id.code,
                } if move.department_analytic_id else None,
            },
            "hierarchy": hierarchy,
            "summary": {
                "total_lines": len(lines),
                "total_amount": total_amount,
                "activities_count": len(hierarchy),
            }
        }

    def _build_hierarchy(self, lines):
        """Build complete hierarchical structure using parent_path for full hierarchy"""
        # Collect all unique analytic accounts from the lines
        all_analytic_ids = set()
        
        for line in lines:
            if line.activity_analytic_id:
                all_analytic_ids.add(line.activity_analytic_id.id)
            if line.department_analytic_id:
                all_analytic_ids.add(line.department_analytic_id.id)
            if line.fund_analytic_id:
                all_analytic_ids.add(line.fund_analytic_id.id)
        
        # Get complete hierarchy paths for all analytic accounts
        hierarchy_paths = self._get_complete_hierarchy_paths(all_analytic_ids)
        
        # Build line data with complete paths
        line_data_with_paths = []
        
        for line in lines:
            # Get the complete paths for this line's analytic accounts
            paths = {
                'activity': self._get_path_hierarchy(line.activity_analytic_id, hierarchy_paths) if line.activity_analytic_id else [],
                'department': self._get_path_hierarchy(line.department_analytic_id, hierarchy_paths) if line.department_analytic_id else [],
                'fund': self._get_path_hierarchy(line.fund_analytic_id, hierarchy_paths) if line.fund_analytic_id else [],
            }
            
            line_data = {
                "id": line.id,
                "account": {
                    "id": line.account_id.id,
                    "name": line.account_id.name,
                    "code": line.account_id.code,
                },
                "balance": line.balance,
                "note": line.note or "",
                "analytic_distribution": line.analytic_distribution or {},
                "paths": paths
            }
            
            line_data_with_paths.append(line_data)
        
        # Build the hierarchy tree from the paths
        return self._build_tree_from_paths(line_data_with_paths)

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

    def _build_tree_from_paths(self, line_data_with_paths):
        """Build tree structure from line data with complete paths"""
        # Group lines by their complete paths
        tree_structure = {}
        
        for line_data in line_data_with_paths:
            # Create a unique path key combining all dimensions
            path_key = self._create_path_key(line_data['paths'])
            
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
        return self._convert_to_hierarchy_tree(tree_structure)

    def _create_path_key(self, paths):
        """Create a unique key from the complete paths"""
        key_parts = []
        
        # Activity path
        if paths.get('activity'):
            activity_codes = [acc['code'] for acc in paths['activity']]
            key_parts.append('A:' + '|'.join(activity_codes))
        
        # Department path  
        if paths.get('department'):
            dept_codes = [acc['code'] for acc in paths['department']]
            key_parts.append('D:' + '|'.join(dept_codes))
        
        # Fund path
        if paths.get('fund'):
            fund_codes = [acc['code'] for acc in paths['fund']]
            key_parts.append('F:' + '|'.join(fund_codes))
        
        return '||'.join(key_parts)

    def _convert_to_hierarchy_tree(self, tree_structure):
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
            
            # Add department hierarchy
            dept_path = paths.get('department', [])
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
            for i, fund_node in enumerate(fund_path):
                node_key = f"fund_{fund_node['code']}"
                
                if node_key not in current_level:
                    current_level[node_key] = {
                        "key": node_key,
                        "type": "fund", 
                        "level": len(activity_path) + len(dept_path) + i + 1,
                        "name": fund_node['name'],
                        "code": fund_node['code'],
                        "children": {},
                        "total_amount": 0,
                        "line_count": 0,
                        "expanded": False,
                    }
                
                current_level = current_level[node_key]["children"]
            
            # Add accounts and lines
            for account_key, account_data in path_data['accounts'].items():
                account_node_key = f"account_{account_key}"
                
                if account_node_key not in current_level:
                    current_level[account_node_key] = {
                        "key": account_node_key,
                        "type": "account",
                        "level": len(activity_path) + len(dept_path) + len(fund_path) + 1,
                        "name": account_data['account']['name'],
                        "code": account_key,
                        "children": {},
                        "total_amount": 0,
                        "line_count": 0,
                        "expanded": False,
                    }
                
                # Add individual lines
                account_children = current_level[account_node_key]["children"]
                for line in account_data['lines']:
                    line_key = f"line_{line['id']}"
                    account_children[line_key] = {
                        "key": line_key,
                        "type": "line",
                        "level": len(activity_path) + len(dept_path) + len(fund_path) + 2,
                        "name": line['note'] or "รายการ",
                        "code": "",
                        "children": {},
                        "total_amount": line['balance'],
                        "line_count": 1,
                        "line_data": line,
                        "expanded": False,
                    }
                    
                    # Update totals
                    current_level[account_node_key]["total_amount"] += line['balance']
                    current_level[account_node_key]["line_count"] += 1
        
        # Convert to list format and calculate totals
        return self._convert_dict_to_list_and_calculate_totals(root_nodes)

    def _convert_dict_to_list_and_calculate_totals(self, nodes_dict):
        """Convert dictionary structure to list and calculate totals"""
        result = []
        
        for node_key, node_data in nodes_dict.items():
            # Convert children
            if node_data["children"]:
                node_data["children"] = self._convert_dict_to_list_and_calculate_totals(node_data["children"])
                
                # Calculate totals from children only for parent nodes (not account nodes)
                if node_data["type"] != "account":
                    node_data["total_amount"] = 0
                    node_data["line_count"] = 0
                    for child in node_data["children"]:
                        node_data["total_amount"] += child["total_amount"]
                        node_data["line_count"] += child["line_count"]
            
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