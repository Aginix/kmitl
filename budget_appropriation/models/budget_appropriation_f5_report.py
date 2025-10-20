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
        """Generate F5 hierarchical data for single budget appropriation"""
        if options is None:
            options = {}

        appropriation = self.env["budget.appropriation"].browse(appropriation_id)

        if not appropriation:
            return {"error": "Invalid appropriation"}

        # Validate EXPENSE type only
        if appropriation.budget_type != 'expense':
            return {"error": "F5 report is only available for expense type appropriations"}

        # Get appropriation lines
        lines = appropriation.line_ids

        # Build hierarchy: Activities → Funds → Budget Accounts → Lines
        hierarchy = self._build_hierarchy(lines)

        # Calculate totals
        amount_total = sum(line.balance for line in lines)

        return {
            "department": self._get_complete_name_without_codes(appropriation.department_analytic_id),
            "type": "รายจ่าย" if appropriation.budget_type == 'expense' else "รายรับ",
            "source": appropriation.source_analytic_id.name,
            "fiscal_year": appropriation.account_fiscal_year_id.name,
            "amount_total": amount_total,
            "hierarchy": hierarchy,
            "summary": {
                "total_lines": len(lines),
                "amount_total": amount_total,
                "activities_count": len(hierarchy),
            }
        }

    @api.model
    def get_f5_data_flat(self, appropriation_id):
        """Generate F5 hierarchical data for single budget appropriation"""
        appropriation = self.env["budget.appropriation"].browse(appropriation_id)

        if not appropriation:
            return {"error": "Invalid appropriation"}

        # Validate EXPENSE type only
        if appropriation.budget_type != 'expense':
            return {"error": "F5 report is only available for expense type appropriations"}

        # Get appropriation lines
        lines = appropriation.line_ids

        # Build hierarchy: Activities → Funds → Budget Accounts → Lines
        hierarchy = self._build_hierarchy(lines, True)

        # Calculate totals
        amount_total = sum(line.balance for line in lines)

        return {
            "department": self._get_complete_name_without_codes(appropriation.department_analytic_id),
            "type": "รายจ่าย" if appropriation.budget_type == 'expense' else "รายรับ",
            "source": appropriation.source_analytic_id.name,
            "fiscal_year": appropriation.account_fiscal_year_id.name,
            "amount_total": amount_total,
            "hierarchy": hierarchy,
            "summary": {
                "total_lines": len(lines),
                "amount_total": amount_total,
                "activities_count": len(hierarchy),
            }
        }

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

