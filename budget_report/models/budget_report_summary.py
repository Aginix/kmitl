# -*- coding: utf-8 -*-
import logging

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from .budget_tree import BudgetTree

_logger = logging.getLogger(__name__)

BUDGET_TYPE = "revenue"


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
            ("date_range_fy_id", "=", fiscal_year.id),
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
            ("date_range_fy_id", "=", fiscal_year.id),
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

        def traverse(node, level=0):
            row_data = node.to_dict()
            row_data["margin_level"] = str(level * 20) + "px"
            rows.append(row_data)

            # Process children - sort them at each level
            sorted_children = self._sort(node.children, level + 1)
            for child in sorted_children:
                traverse(child, level + 1)

        # Start from root's children (skip root itself)
        sorted_roots = self._sort(roots, 0)
        for child in sorted_roots:
            traverse(child, 0)

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
                "has_data": self._department_has_data(dept),
            }
            dept_dict[dept.id] = dept_data
            
            if dept.parent_id:
                parent = dept_dict.get(dept.parent_id.id)
                if parent:
                    parent["children"].append(dept_data)
            else:
                roots.append(dept_data)
        
        return roots

    def _department_has_data(self, department):
        """Check if department has budget data"""
        has_moves = self.env["budget.move.line"].search_count([
            ("department_analytic_id", "=", department.id),
            ("parent_state", "=", "posted"),
        ], limit=1)
        
        has_commitments = self.env["budget.commitment"].search_count([
            ("department_analytic_id", "=", department.id),
            ("state", "in", ["reserved", "obligated"]),
        ], limit=1)
        
        return bool(has_moves or has_commitments)

    @api.model
    def get_filter_options(self):
        return {
            "state": [{"id": "draft"}, {"id": "review"}, {"id": "posted"}],
            "fiscal_years": self._get_fiscal_year_options(),
            "source_analytics": self._get_source_analytics_options(),
            "departments": self._get_department_hierarchy(),
        }
