import logging
import re

from odoo import api, fields, models
from ..utils.tree_builder import BudgetTreeBuilder, TreeConfig, BudgetTreeExporter

_logger = logging.getLogger(__name__)


class BudgetAppropriationF4Report(models.TransientModel):
    _name = "budget.appropriation.f4.report"
    _description = "Budget Appropriation F4 Report"

    appropriation_id = fields.Many2one(
        "budget.appropriation", string="Budget Appropriation", required=True
    )

    @api.model
    def get_f4_data(self, appropriation_id, options=None):
        """
        Generate F4 hierarchical data for revenue budget appropriation(s).

        Args:
            appropriation_id: int or list of int - single ID or list of IDs
            options: dict with optional keys:
                - department_name: str - override department name for merged report

        Returns:
            dict: F4 report data with hierarchy, totals, and metadata
        """
        if options is None:
            options = {}

        # Normalize to list for unified handling
        if isinstance(appropriation_id, int):
            appropriation_ids = [appropriation_id]
        else:
            appropriation_ids = appropriation_id

        appropriations = self.env["budget.appropriation"].browse(appropriation_ids)

        # Validate appropriations
        error = self._validate_appropriations(appropriations)
        if error:
            return {"error": error}

        # Merge lines from all appropriations
        lines = appropriations.mapped("line_ids")
        deduct_lines = appropriations.mapped("deduct_line_ids")

        # Build hierarchies
        hierarchy = self._build_hierarchy(lines)
        deduct_hierarchy = self._build_hierarchy(deduct_lines)

        # Calculate totals
        amount_total = sum(line.balance for line in lines)
        amount_deduct = sum(line.balance for line in deduct_lines)
        amount_net = amount_total - amount_deduct

        # Get metadata from first appropriation
        first = appropriations[0]
        if len(appropriations) > 1:
            department_name = options.get(
                "department_name",
                self._get_complete_name_without_codes(first.department_analytic_id),
            )
        else:
            department_name = self._get_complete_name_without_codes(
                first.department_analytic_id
            )

        return {
            "appropriation": {
                "id": first.id,
                "name": first.name,
                "date": first.date.strftime("%d/%m/%Y") if first.date else "",
                "state": first.state,
                "amount_total": amount_total,
                "amount_deduct": amount_deduct,
                "amount_net": amount_net,
                "currency_symbol": first.currency_id.symbol or "฿",
                "fiscal_year": {
                    "id": first.account_fiscal_year_id.id,
                    "name": first.account_fiscal_year_id.name,
                }
                if first.account_fiscal_year_id
                else None,
                "department": {
                    "id": first.department_analytic_id.id,
                    "name": first.department_analytic_id.name,
                    "code": first.department_analytic_id.code,
                    "complete_name": department_name,
                }
                if first.department_analytic_id
                else None,
                "source": {
                    "id": first.source_analytic_id.id,
                    "name": first.source_analytic_id.name,
                    "code": first.source_analytic_id.code,
                }
                if first.source_analytic_id
                else None,
            },
            "department": department_name,
            "source": first.source_analytic_id.name if first.source_analytic_id else "",
            "fiscal_year": first.account_fiscal_year_id.name
            if first.account_fiscal_year_id
            else "",
            "amount_total": amount_total,
            "amount_deduct": amount_deduct,
            "amount_net": amount_net,
            "hierarchy": hierarchy,
            "deduct_hierarchy": deduct_hierarchy,
            "summary": {
                "total_lines": len(lines),
                "amount_total": amount_total,
                "accounts_count": len(hierarchy),
                "appropriations_count": len(appropriations),
            },
        }

    def _validate_appropriations(self, appropriations):
        """
        Validate all appropriations are revenue type.

        Returns:
            str: error message if validation fails, None if valid
        """
        if not appropriations:
            return "No appropriations selected"

        non_revenue = appropriations.filtered(lambda a: a.budget_type != "revenue")
        if non_revenue:
            return "F4 report is only available for revenue type appropriations"

        return None

    def _build_hierarchy(self, lines):
        """Build hierarchical tree structure for revenue: Account only"""

        if not lines:
            return []

        # Configure tree builder for F4 reports (revenue - accounts only)
        config = TreeConfig.for_f4_report()
        tree_builder = BudgetTreeBuilder(config)

        # Build tree from lines
        tree = tree_builder.build_tree(lines)

        # Export to Odoo-compatible format
        return BudgetTreeExporter.to_odoo_hierarchy(tree)

    def _get_complete_name_without_codes(self, record):
        """Get complete name without codes - helper method for appropriation data"""
        if not record:
            return ""

        if hasattr(record, "complete_name") and record.complete_name:
            return re.sub(r"\[.*?\]\s*", "", record.complete_name)
        return record.name
