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
        move_lines = self.env["budget.move.line"].search(
            [
                ("parent_state", "=", "posted"),
                ("date_range_fy_id", "=", fiscal_year.id),
                ("source_analytic_id", "=", source_analytic.id),
            ],
            order="date desc",
        )
        commitment_lines = self.env["budget.commitment"].search(
            [
                ("state", "in", ["reserved", "obligated"]),
                ("date_range_fy_id", "=", fiscal_year.id),
                ("source_analytic_id", "=", source_analytic.id),
            ],
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
            },
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

    @api.model
    def get_filter_options(self):
        return {
            "state": [{"id": "draft"}, {"id": "review"}, {"id": "posted"}],
            "fiscal_years": self._get_fiscal_year_options(),
            "source_analytics": self._get_source_analytics_options(),
        }
