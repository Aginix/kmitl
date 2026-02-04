import logging

from odoo import api, fields, models, _
from ..utils.tree_builder import BudgetTreeBuilder, TreeConfig, BudgetTreeExporter

_logger = logging.getLogger(__name__)


class BudgetAppropriationF5Report(models.TransientModel):
    _name = "budget.appropriation.f5.report"
    _description = "Budget Appropriation F5 Report"

    appropriation_id = fields.Many2one("budget.appropriation", string="Budget Appropriation", required=True)

    @api.model
    def get_f5_data(self, appropriation_id, options=None):
        """
        Generate F5 hierarchical data for budget appropriation(s).

        Args:
            appropriation_id: int or list of int - single ID or list of IDs
            options: dict with optional keys:
                - department_name: str - override department name for merged report

        Returns:
            dict: F5 report data with hierarchy, totals, and metadata
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

        # Build hierarchy: Activities → Funds → Budget Accounts → Lines
        hierarchy = self._build_hierarchy(lines)

        # Calculate totals
        amount_total = sum(line.balance for line in lines)

        # Get metadata - use options or derive from appropriations
        first = appropriations[0]
        if len(appropriations) > 1:
            department = options.get("department_name", "รวมหลายหน่วยงาน")
        else:
            department = self._get_complete_name_without_codes(first.department_analytic_id)

        return {
            "department": department,
            "type": "รายจ่าย" if first.budget_type == 'expense' else "รายรับ",
            "source": first.source_analytic_id.name,
            "fiscal_year": first.account_fiscal_year_id.name,
            "amount_total": amount_total,
            "hierarchy": hierarchy,
            "summary": {
                "total_lines": len(lines),
                "amount_total": amount_total,
                "activities_count": len(hierarchy),
                "appropriations_count": len(appropriations),
            }
        }

    @api.model
    def get_f5_data_flat(self, appropriation_id, options=None):
        """
        Generate F5 flat data for budget appropriation(s).

        Args:
            appropriation_id: int or list of int - single ID or list of IDs
            options: dict with optional keys:
                - department_name: str - override department name for merged report

        Returns:
            dict: F5 report data with flattened hierarchy
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

        # Build hierarchy: Activities → Funds → Budget Accounts → Lines
        hierarchy = self._build_hierarchy(lines, True)

        # Calculate totals
        amount_total = sum(line.balance for line in lines)

        # Get metadata - use options or derive from appropriations
        first = appropriations[0]
        if len(appropriations) > 1:
            department = options.get("department_name", "รวมหลายหน่วยงาน")
        else:
            department = self._get_complete_name_without_codes(first.department_analytic_id)

        return {
            "department": department,
            "type": "รายจ่าย" if first.budget_type == 'expense' else "รายรับ",
            "source": first.source_analytic_id.name,
            "fiscal_year": first.account_fiscal_year_id.name,
            "amount_total": amount_total,
            "hierarchy": hierarchy,
            "summary": {
                "total_lines": len(lines),
                "amount_total": amount_total,
                "activities_count": len(hierarchy),
                "appropriations_count": len(appropriations),
            }
        }

    def _validate_appropriations(self, appropriations):
        """
        Validate all appropriations have consistent required values.

        Args:
            appropriations: recordset of budget.appropriation

        Returns:
            str: error message if validation fails, None if valid
        """
        if not appropriations:
            return "No appropriations selected"

        # All must be expense type
        non_expense = appropriations.filtered(lambda a: a.budget_type != 'expense')
        if non_expense:
            return "F5 report is only available for expense type appropriations"

        # source_analytic_id must be same across all
        sources = appropriations.mapped("source_analytic_id")
        if len(sources) > 1:
            names = ", ".join(s.name for s in sources)
            return f"แหล่งเงินต้องเหมือนกัน (พบ: {names})"

        # account_fiscal_year_id must be same across all
        years = appropriations.mapped("account_fiscal_year_id")
        if len(years) > 1:
            names = ", ".join(y.name for y in years)
            return f"ปีงบประมาณต้องเหมือนกัน (พบ: {names})"

        return None

    def _build_hierarchy(self, lines, flatten=False):
        """Build hierarchical tree structure: Activity → Fund → Account"""

        if not lines:
            return []

        # Configure tree builder for F5 reports
        config = TreeConfig.for_f5_report()
        tree_builder = BudgetTreeBuilder(config)

        # Build tree from lines
        tree = tree_builder.build_tree(lines)

        if flatten:
            return BudgetTreeExporter.to_flat_list(tree)

        # Export to Odoo-compatible format
        return BudgetTreeExporter.to_odoo_hierarchy(tree)

    def _get_complete_name_without_codes(self, record):
        """Get complete name without codes - helper method for appropriation data"""
        if not record:
            return ""

        if hasattr(record, 'complete_name') and record.complete_name:
            # Remove codes from complete_name
            import re
            return re.sub(r'\[.*?\]\s*', '', record.complete_name)
        return record.name

