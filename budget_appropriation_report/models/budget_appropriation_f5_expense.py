# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationF5Expense(models.AbstractModel):
    _name = "budget.appropriation.f5.expense"
    _description = "Budget Appropriation F5 Expense Report"

    @api.model
    def get_data(self, filters=None):
        """Get F5 expense report data with hierarchical structure"""
        if filters is None:
            filters = {}

        # Get filter values
        fiscal_year_id = filters.get("fiscal_year_id")
        department_id = filters.get("department_id")
        source_analytic_id = filters.get("source_analytic_id")

        # Get or default fiscal year
        if fiscal_year_id:
            fiscal_year = self.env["account.fiscal.year"].browse(fiscal_year_id)
        else:
            fiscal_year = self.env["account.fiscal.year"].search(
                [], limit=1, order="date_from DESC"
            )
            if not fiscal_year:
                raise UserError(_("No fiscal year found"))

        # Get or default source analytic
        if source_analytic_id:
            source_analytic = self.env["account.analytic.account"].browse(source_analytic_id)
        else:
            # Default to government budget source (source code "1")
            source_analytic = self.env["account.analytic.account"].search([
                ("root_plan_id.code", "=", "sources"),
                ("code", "=", "1")
            ], limit=1)
            if not source_analytic:
                raise UserError(_("Default source analytic account not found"))

        # Use fiscal year date range
        date_from = fiscal_year.date_from
        date_to = fiscal_year.date_to

        # Build domain for appropriation lines
        appropriation_domain = [
            ("appropriation_id.budget_type", "=", "expense"),
            ("appropriation_id.state", "=", "posted"),
            ("appropriation_id.date_range_fy_id", "=", fiscal_year.id),
            ("appropriation_id.source_analytic_id", "=", source_analytic.id),
        ]

        # Add date filters
        appropriation_domain.append(("appropriation_id.date", ">=", date_from))
        appropriation_domain.append(("appropriation_id.date", "<=", date_to))

        # Add department filter
        if department_id:
            all_dept_ids = self._get_department_with_children([department_id])
            appropriation_domain.append(("appropriation_id.department_analytic_id", "in", all_dept_ids))

        # Get appropriation lines
        appropriation_lines = self.env["budget.appropriation.line"].search(appropriation_domain)

        # Build hierarchical tree
        hierarchy = self._build_hierarchy(appropriation_lines)

        # Calculate summary data
        total_amount = sum(line.balance for line in appropriation_lines)
        total_lines = len(appropriation_lines)
        activities_count = len(hierarchy)

        return {
            "hierarchy": hierarchy,
            "summary": {
                "total_amount": total_amount,
                "total_lines": total_lines,
                "activities_count": activities_count,
            },
            "filters": {
                "fiscal_year": {
                    "id": fiscal_year.id,
                    "name": fiscal_year.name,
                    "date_from": fiscal_year.date_from.strftime("%Y-%m-%d"),
                    "date_to": fiscal_year.date_to.strftime("%Y-%m-%d"),
                },
                "source_analytic": {
                    "id": source_analytic.id,
                    "code": source_analytic.code,
                    "name": source_analytic.name,
                },
                "department": self._get_selected_department(department_id) if department_id else None,
                "date_from": date_from.strftime("%Y-%m-%d"),
                "date_to": date_to.strftime("%Y-%m-%d"),
            },
            "current_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @api.model
    def get_filter_options(self):
        """Get available filter options"""
        fiscal_years = self.env["account.fiscal.year"].search([], order="date_from DESC")
        departments = self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "departments")
        ], order="code")
        sources = self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "sources")
        ], order="code")

        return {
            "fiscal_years": [{
                "id": fy.id,
                "name": fy.name,
                "date_from": fy.date_from.strftime("%Y-%m-%d"),
                "date_to": fy.date_to.strftime("%Y-%m-%d"),
            } for fy in fiscal_years],
            "departments": self._build_department_hierarchy(),
            "sources": [{
                "id": source.id,
                "code": source.code,
                "name": source.name,
            } for source in sources],
        }

    def _build_hierarchy(self, appropriation_lines):
        """Build complete hierarchical tree from root to leaf including all intermediate nodes"""
        if not appropriation_lines:
            return []

        # Step 1: Get all activities and build complete tree structure
        all_activities = self._get_complete_activity_hierarchy(appropriation_lines)
        all_funds = self._get_all_funds()
        all_accounts = self._get_all_budget_accounts()

        # Step 2: Build data mapping from appropriation lines
        line_data_map = self._build_line_data_map(appropriation_lines)

        # Step 3: Build complete hierarchy tree
        hierarchy = self._build_complete_tree(all_activities, all_funds, all_accounts, line_data_map)

        return hierarchy

    def _get_complete_activity_hierarchy(self, appropriation_lines):
        """Get complete activity hierarchy including all parent nodes"""
        # Get all activities mentioned in the lines
        activity_ids = set()
        for line in appropriation_lines:
            if line.activity_analytic_id:
                activity_ids.add(line.activity_analytic_id.id)

        if not activity_ids:
            return []

        # Get all activities and their complete parent hierarchy
        activities = self.env["account.analytic.account"].browse(list(activity_ids))
        complete_activity_ids = set(activity_ids)

        # Add all parent activities to ensure complete hierarchy
        for activity in activities:
            if activity.parent_path:
                parent_ids = [int(pid) for pid in activity.parent_path.strip('/').split('/') if pid]
                complete_activity_ids.update(parent_ids)

        # Get all activities in hierarchy order
        all_activities = self.env["account.analytic.account"].browse(list(complete_activity_ids))
        return all_activities.sorted(key=lambda a: (a.parent_path or '', a.code or ''))

    def _get_all_funds(self):
        """Get all funds"""
        return self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "funds")
        ], order="code")

    def _get_all_budget_accounts(self):
        """Get all budget accounts"""
        return self.env["budget.account"].search([
            ("budget_type", "=", "expense")
        ], order="code")

    def _build_line_data_map(self, appropriation_lines):
        """Build mapping of line data by activity, fund, and account"""
        line_data_map = {}

        for line in appropriation_lines:
            activity_id = line.activity_analytic_id.id if line.activity_analytic_id else None
            fund_id = line.fund_analytic_id.id if line.fund_analytic_id else None
            account_id = line.account_id.id if line.account_id else None

            key = (activity_id, fund_id, account_id)

            if key not in line_data_map:
                line_data_map[key] = {
                    'amount': 0.0,
                    'lines': []
                }

            line_data_map[key]['amount'] += line.balance
            line_data_map[key]['lines'].append({
                "id": line.id,
                "name": line.name or _("Appropriation Line"),
                "amount": line.balance,
                "appropriation_name": line.appropriation_id.name,
                "appropriation_date": line.appropriation_id.date.strftime("%d/%m/%Y") if line.appropriation_id.date else "",
            })

        return line_data_map

    def _build_complete_tree(self, all_activities, all_funds, all_accounts, line_data_map):
        """Build complete hierarchical tree structure"""
        # Build activity hierarchy first
        activity_tree = self._build_activity_tree(all_activities, line_data_map, all_funds, all_accounts)
        return activity_tree

    def _build_activity_tree(self, all_activities, line_data_map, all_funds, all_accounts):
        """Build activity tree with complete hierarchy"""
        activity_nodes = {}
        root_activities = []

        # Create all activity nodes
        for activity in all_activities:
            node = {
                "key": f"activity_{activity.id}",
                "type": "activity",
                "id": activity.id,
                "code": activity.code or "",
                "name": activity.name or "",
                "complete_name": self._get_complete_name_without_codes(activity),
                "amount": 0.0,
                "total_amount": 0.0,
                "level": len(activity.parent_path.strip('/').split('/')) - 1 if activity.parent_path else 0,
                "children": [],
                "line_details": [],
                "parent_id": activity.parent_id.id if activity.parent_id else None,
            }
            activity_nodes[activity.id] = node

        # Build parent-child relationships
        for activity in all_activities:
            node = activity_nodes[activity.id]
            if activity.parent_id and activity.parent_id.id in activity_nodes:
                activity_nodes[activity.parent_id.id]["children"].append(node)
            else:
                root_activities.append(node)

        # Add funds and accounts to leaf activities that have data
        for activity in all_activities:
            if self._has_data_for_activity(activity.id, line_data_map):
                self._add_funds_to_activity(activity_nodes[activity.id], all_funds, all_accounts, line_data_map, activity.id)

        # Calculate totals bottom-up
        for node in root_activities:
            self._calculate_totals(node)

        # Sort children at each level
        for node in root_activities:
            self._sort_tree_children(node)

        return root_activities

    def _has_data_for_activity(self, activity_id, line_data_map):
        """Check if activity has any data"""
        for (act_id, fund_id, account_id), data in line_data_map.items():
            if act_id == activity_id and data['amount'] != 0:
                return True
        return False

    def _add_funds_to_activity(self, activity_node, all_funds, all_accounts, line_data_map, activity_id):
        """Add funds and accounts to activity node"""
        for fund in all_funds:
            fund_has_data = False
            fund_node = {
                "key": f"{activity_node['key']}_fund_{fund.id}",
                "type": "fund",
                "id": fund.id,
                "code": fund.code or "",
                "name": fund.name or "",
                "complete_name": self._get_complete_name_without_codes(fund),
                "amount": 0.0,
                "total_amount": 0.0,
                "level": activity_node["level"] + 1,
                "children": [],
                "line_details": [],
            }

            # Add accounts to fund
            for account in all_accounts:
                key = (activity_id, fund.id, account.id)
                if key in line_data_map and line_data_map[key]['amount'] != 0:
                    fund_has_data = True
                    account_node = {
                        "key": f"{fund_node['key']}_account_{account.id}",
                        "type": "account",
                        "id": account.id,
                        "code": account.code or "",
                        "name": account.name or "",
                        "complete_name": account.name or "",
                        "amount": line_data_map[key]['amount'],
                        "total_amount": line_data_map[key]['amount'],
                        "level": fund_node["level"] + 1,
                        "children": [],
                        "line_details": line_data_map[key]['lines'],
                    }
                    fund_node["children"].append(account_node)
                    fund_node["amount"] += account_node["amount"]

            # Only add fund if it has data
            if fund_has_data:
                fund_node["total_amount"] = fund_node["amount"]
                activity_node["children"].append(fund_node)
                activity_node["amount"] += fund_node["amount"]

    def _calculate_totals(self, node):
        """Calculate totals recursively bottom-up"""
        total = node.get("amount", 0.0)

        for child in node.get("children", []):
            total += self._calculate_totals(child)

        node["total_amount"] = total
        return total

    def _sort_tree_children(self, node):
        """Sort children at each level by code"""
        if "children" in node and node["children"]:
            node["children"].sort(key=lambda x: x.get("code", ""))
            for child in node["children"]:
                self._sort_tree_children(child)

    def _get_department_with_children(self, department_ids):
        """Get department IDs including all children"""
        if not department_ids:
            return []

        departments = self.env["account.analytic.account"].browse(department_ids)
        all_dept_ids = list(department_ids)

        for dept in departments:
            children = self.env["account.analytic.account"].search([
                ("parent_path", "like", f"{dept.parent_path}%"),
                ("id", "!=", dept.id)
            ])
            all_dept_ids.extend(children.ids)

        return list(set(all_dept_ids))

    def _get_selected_department(self, department_id):
        """Get selected department details"""
        if not department_id:
            return None

        department = self.env["account.analytic.account"].browse(department_id)
        return {
            "id": department.id,
            "code": department.code,
            "name": department.name,
            "complete_name": self._get_complete_name_without_codes(department),
        }

    def _build_department_hierarchy(self):
        """Build department hierarchy for filter display"""
        departments = self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "departments"),
            ("parent_id", "=", False)  # Get root departments only
        ], order="code")

        def build_children(parent):
            children = self.env["account.analytic.account"].search([
                ("parent_id", "=", parent.id)
            ], order="code")

            result = []
            for child in children:
                child_data = {
                    "id": child.id,
                    "code": child.code,
                    "name": child.name,
                    "complete_name": self._get_complete_name_without_codes(child),
                    "children": build_children(child)
                }
                result.append(child_data)
            return result

        hierarchy = []
        for dept in departments:
            dept_data = {
                "id": dept.id,
                "code": dept.code,
                "name": dept.name,
                "complete_name": self._get_complete_name_without_codes(dept),
                "children": build_children(dept)
            }
            hierarchy.append(dept_data)

        return hierarchy

    def _get_complete_name_without_codes(self, record):
        """Get complete name without codes"""
        if not record:
            return ""

        if hasattr(record, 'complete_name') and record.complete_name:
            # Remove codes from complete_name
            import re
            return re.sub(r'\[.*?\]\s*', '', record.complete_name)
        return record.name