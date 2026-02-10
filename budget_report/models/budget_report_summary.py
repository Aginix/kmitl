# -*- coding: utf-8 -*-
import logging

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from .budget_tree import BudgetTree

_logger = logging.getLogger(__name__)

class BudgetReportSummary(models.AbstractModel):
    _name = _description = "budget.report.summary"

    @api.model
    def get_data(self, filters):
        fiscal_year_id = filters.get("fiscal_year_id", False)
        department_ids = filters.get("department_ids", [])

        if fiscal_year_id:
            fiscal_year = self.env["account.fiscal.year"].browse(fiscal_year_id)
        else:
            fiscal_year = self.env["account.fiscal.year"].search(
                [], limit=1, order="date_from DESC"
            )
            fiscal_year_id = fiscal_year.id

        source_analytic_id = filters.get("source_analytic_id", False)
        if source_analytic_id:
            source_analytic = self.env["account.analytic.account"].browse(
                source_analytic_id
            )
        else:
            source_analytic = self.env["account.analytic.account"].browse(
                self.env.ref("account_analytic_kmitl.source_2").id
            )

        funds = self.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "funds")], order="code"
        )
        departments = self.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "departments")], order="code"
        )
        activities = self.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "activities")], order="code"
        )
        sources = self.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "sources")], order="code"
        )
        accounts = self.env["budget.account"].search(
            [("budget_type", "=", "expense")], order="code"
        )
        # Build domain for move_lines with department filter
        move_line_domain = [
            ("parent_state", "=", "posted"),
            ("account_fiscal_year_id", "=", fiscal_year.id),
            ("source_analytic_id", "=", source_analytic.id),
        ]

        if department_ids:
            all_dept_ids = self._get_department_with_children(department_ids)
            move_line_domain.append(("department_analytic_id", "in", all_dept_ids))

        move_lines = self.env["budget.move.line"].search(
            move_line_domain,
            order="date desc",
        )
        # Build domain for commitment_lines with department filter
        commitment_domain = [
            ("state", "in", ["reserved", "obligated"]),
            ("account_fiscal_year_id", "=", fiscal_year.id),
            ("source_analytic_id", "=", source_analytic.id),
        ]

        if department_ids:
            commitment_domain.append(("department_analytic_id", "in", all_dept_ids))

        commitment_lines = self.env["budget.commitment"].search(
            commitment_domain,
            order="date desc",
        )

        tree = BudgetTree(
            move_lines=move_lines,
            commitment_lines=commitment_lines,
            accounts=accounts,
            activities=activities,
            departments=departments,
            funds=funds,
            sources=sources,
        )

        dimensions = ["activity", "fund", "account"]
        # dimensions = ["account"]
        # ใช้ method ใหม่ที่รองรับ dynamic dimensions
        root_tree = tree.build_tree(dimensions)
        rows = self._to_flat_table(root_tree)

        for idx, row in enumerate(rows):
            row["id"] = idx + 1

        current_date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        return {
            "rows": rows,
            "fiscal_year": {
                "id": fiscal_year.id,
                "name": fiscal_year.name,
            },
            "source_analytic": {
                "id": source_analytic.id,
                "code": source_analytic.code,
                "name": source_analytic.name,
            },
            "filters": {
                "fiscal_year_id": fiscal_year.id,
                "date_from": fiscal_year.date_from.strftime("%Y-%m-%d"),
                "date_to": fiscal_year.date_to.strftime("%Y-%m-%d"),
                "source_analytic_id": source_analytic.id,
                "department_ids": department_ids,
            },
            "departments": self._get_department_hierarchy(),
            "current_date": current_date,
        }

    def _sort(self, nodes, level):
        """
        Sort nodes with custom priority:
        1. Codes starting with "09" first
        2. Codes starting with "06" second
        3. Everything else sorted alphabetically by code
        """
        if level == 0:

            def sort_key(node):
                code = node.value["code"]
                if code == "09":
                    return (0, code)  # Highest priority
                elif code == "06":
                    return (1, code)  # Second priority
                else:
                    return (2, code)  # Alphabetical order for the rest

            return sorted(nodes, key=sort_key)

        # Sort by code for other levels
        def sort_key(node):
            code = node.value["code"]
            return code

        return sorted(nodes, key=sort_key)

    def _to_flat_table(self, roots):
        rows = []
        parent_map = {}  # Track parent-child relationships

        def traverse(node, level=0, parent_id=None, parent_contexts=None):
            if parent_contexts is None:
                parent_contexts = {}

            row_data = node.to_dict()
            row_data["margin_level"] = str(level * 20) + "px"
            row_data["level"] = level
            row_data["parent_row_id"] = parent_id
            row_data["has_children"] = len(node.children) > 0

            # Generate unique row key for expand/collapse tracking
            row_data["row_key"] = f"{node.node_type}_{node.value['code']}_{node.value['id']}"

            # Add parent context for multi-dimensional filtering
            if node.node_type == "activity":
                parent_contexts["activity"] = {
                    "id": node.value["id"],
                    "code": node.value.get("code", ""),
                    "path": node.value.get("parent_path", ""),
                }
            elif node.node_type == "fund":
                parent_contexts["fund"] = {
                    "id": node.value["id"],
                    "code": node.value.get("code", ""),
                    "path": node.value.get("parent_path", ""),
                }
                # Include parent activity context
                if "activity" in parent_contexts:
                    row_data["parent_activity_id"] = parent_contexts["activity"]["id"]
                    row_data["parent_activity_code"] = parent_contexts["activity"]["code"]
                    row_data["parent_activity_path"] = parent_contexts["activity"]["path"]
            elif node.node_type == "account":
                # Include all parent contexts
                if "activity" in parent_contexts:
                    row_data["parent_activity_id"] = parent_contexts["activity"]["id"]
                    row_data["parent_activity_code"] = parent_contexts["activity"]["code"]
                    row_data["parent_activity_path"] = parent_contexts["activity"]["path"]
                if "fund" in parent_contexts:
                    row_data["parent_fund_id"] = parent_contexts["fund"]["id"]
                    row_data["parent_fund_code"] = parent_contexts["fund"]["code"]
                    row_data["parent_fund_path"] = parent_contexts["fund"]["path"]

            # Add to parent tracking
            if parent_id:
                if parent_id not in parent_map:
                    parent_map[parent_id] = []
                parent_map[parent_id].append(row_data["row_key"])

            rows.append(row_data)
            current_row_id = row_data["row_key"]

            # Process children with updated context
            sorted_children = self._sort(node.children, level + 1)
            for child in sorted_children:
                traverse(child, level + 1, current_row_id, parent_contexts.copy())

        # Start from root's children (skip root itself)
        sorted_roots = self._sort(roots, 0)
        for child in sorted_roots:
            traverse(child, 0)

        # Add parent-child mapping to each row
        for row in rows:
            row["child_keys"] = parent_map.get(row["row_key"], [])

        _logger.info(f"Converted tree to flat table with {len(rows)} rows")
        return rows

    def _get_fiscal_year_options(self):
        data = self.env["account.fiscal.year"].search([], order="date_from DESC")
        return [
            dict(
                id=n.id,
                name=n.name,
                date_from=n.date_from.strftime("%Y-%m-%d"),
                date_to=n.date_to.strftime("%Y-%m-%d"),
            )
            for n in data
        ]

    def _get_source_analytics_options(self):
        data = self.env["account.analytic.account"].search(
            [("plan_id.code", "=", "sources")], order="code ASC"
        )
        return [
            dict(id=n.id, code=n.code, name=n.name, complete_name=n.complete_name)
            for n in data
        ]

    def _get_department_with_children(self, department_ids):
        """Get department IDs including all children"""
        if not department_ids:
            return []

        departments = self.env["account.analytic.account"].browse(department_ids)
        all_ids = set(department_ids)

        for dept in departments:
            # Use parent_path for efficient child retrieval
            children = self.env["account.analytic.account"].search([
                ("parent_path", "=like", f"{dept.parent_path}%"),
                ("root_plan_id.code", "=", "departments"),
            ])
            all_ids.update(children.ids)

        return list(all_ids)

    def _get_department_hierarchy(self):
        """Build department hierarchy for frontend"""
        departments = self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "departments"),
        ], order="code,name")

        # Batch query: get all department IDs that have data (2 queries total)
        move_dept_ids = set(
            r["department_analytic_id"][0]
            for r in self.env["budget.move.line"].read_group(
                [("parent_state", "=", "posted")],
                ["department_analytic_id"],
                ["department_analytic_id"],
            )
            if r["department_analytic_id"]
        )
        commitment_dept_ids = set(
            r["department_analytic_id"][0]
            for r in self.env["budget.commitment"].read_group(
                [("state", "in", ["reserved", "obligated"])],
                ["department_analytic_id"],
                ["department_analytic_id"],
            )
            if r["department_analytic_id"]
        )
        depts_with_data = move_dept_ids | commitment_dept_ids

        # Build hierarchy structure
        dept_dict = {}
        roots = []

        for dept in departments:
            dept_data = {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "complete_name": dept.complete_name,
                "children": [],
                "has_data": dept.id in depts_with_data,
            }
            dept_dict[dept.id] = dept_data

            if dept.parent_id:
                parent = dept_dict.get(dept.parent_id.id)
                if parent:
                    parent["children"].append(dept_data)
            else:
                roots.append(dept_data)

        return roots

    @api.model
    def get_filter_options(self):
        return {
            "state": [{"id": "draft"}, {"id": "review"}, {"id": "posted"}],
            "fiscal_years": self._get_fiscal_year_options(),
            "source_analytics": self._get_source_analytics_options(),
            "departments": self._get_department_hierarchy(),
        }

    @api.model
    def get_analytic_children(self, analytic_id, dimension):
        """Get all child analytic account IDs for hierarchical filtering"""
        analytic = self.env["account.analytic.account"].browse(analytic_id)
        if not analytic.exists():
            return [analytic_id]

        # Use parent_path for efficient child retrieval
        children = self.env["account.analytic.account"].search([
            ("parent_path", "=like", f"{analytic.parent_path}%"),
            ("root_plan_id.code", "=", dimension),
        ])

        return children.ids

    @api.model
    def get_budget_account_children(self, account_id):
        """Get all child budget account IDs for hierarchical filtering"""
        account = self.env["budget.account"].browse(account_id)
        if not account.exists():
            return [account_id]

        # Use parent_path for efficient child retrieval
        children = self.env["budget.account"].search([
            ("parent_path", "=like", f"{account.parent_path}%"),
        ])

        return children.ids

    @api.model
    def get_budget_accounts_for_activity(self, activity_id):
        """Get all budget account IDs that are used with this activity"""
        # Get all child activities under this activity
        activity_children = self.get_analytic_children(activity_id, 'activities')

        # Find all budget accounts that have data under these activities
        move_lines = self.env["budget.move.line"].search([
            ('activity_analytic_id', 'in', activity_children),
            ('parent_state', '=', 'posted'),
        ])
        commitments = self.env["budget.commitment"].search([
            ('activity_analytic_id', 'in', activity_children),
            ('state', 'in', ['reserved', 'obligated']),
        ])

        account_ids = set()
        account_ids.update(move_lines.mapped('account_id').ids)
        account_ids.update(commitments.mapped('account_id').ids)

        return list(account_ids)

    @api.model
    def get_budget_accounts_for_fund(self, fund_id, parent_activity_id=None):
        """Get all budget account IDs that are used with this fund (and optionally parent activity)"""
        # Get all child funds under this fund
        fund_children = self.get_analytic_children(fund_id, 'funds')

        domain_move = [
            ('fund_analytic_id', 'in', fund_children),
            ('parent_state', '=', 'posted'),
        ]
        domain_commitment = [
            ('fund_analytic_id', 'in', fund_children),
            ('state', 'in', ['reserved', 'obligated']),
        ]

        # If parent activity is specified, also filter by activity
        if parent_activity_id:
            activity_children = self.get_analytic_children(parent_activity_id, 'activities')
            domain_move.append(('activity_analytic_id', 'in', activity_children))
            domain_commitment.append(('activity_analytic_id', 'in', activity_children))

        # Find all budget accounts that have data under these funds
        move_lines = self.env["budget.move.line"].search(domain_move)
        commitments = self.env["budget.commitment"].search(domain_commitment)

        account_ids = set()
        account_ids.update(move_lines.mapped('account_id').ids)
        account_ids.update(commitments.mapped('account_id').ids)

        return list(account_ids)

    @api.model
    def get_analytic_ids_by_code_prefix(self, code_prefix, field_name):
        """Get analytic account IDs that start with the given code prefix"""
        # Map field names to dimensions
        dimension_map = {
            'activity_analytic_id': 'activities',
            'fund_analytic_id': 'funds',
            'source_analytic_id': 'sources',
            'department_analytic_id': 'departments',
        }

        dimension = dimension_map.get(field_name)
        if not dimension:
            _logger.warning(f"Unknown analytic field: {field_name}")
            return []

        # Search analytic accounts by code prefix
        analytics = self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", dimension),
            ("code", "=ilike", f"{code_prefix}%"),
        ])

        _logger.info(f"Found {len(analytics)} analytic accounts for {field_name} with code prefix {code_prefix}")
        return analytics.ids

    @api.model
    def get_budget_account_ids_by_code_prefix(self, code_prefix, parent_code_prefix=None):
        """Get budget account IDs that start with the given code prefix"""
        domain = [("code", "=ilike", f"{code_prefix}%")]

        # If parent code is provided, also filter by parent context
        # This can be used for more specific filtering if needed

        accounts = self.env["budget.account"].search(domain)

        _logger.info(f"Found {len(accounts)} budget accounts with code prefix {code_prefix}")
        return accounts.ids
