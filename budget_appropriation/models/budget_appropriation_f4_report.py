import logging

from odoo import api, fields, models, _
from ..utils.tree_builder import BudgetTreeBuilder, TreeConfig, BudgetTreeExporter

_logger = logging.getLogger(__name__)


class BudgetAppropriationF4Report(models.TransientModel):
    _name = "budget.appropriation.f4.report"
    _description = "Budget Appropriation F4 Report"

    appropriation_id = fields.Many2one("budget.appropriation", string="Budget Appropriation", required=True)

    @api.model
    def get_f4_data(self, appropriation_id, options=None):
        """Generate F4 hierarchical data for revenue budget appropriation"""
        if options is None:
            options = {}
        
        appropriation = self.env["budget.appropriation"].browse(appropriation_id)
        
        if not appropriation:
            return {"error": "Invalid appropriation"}
        
        # Validate REVENUE type only
        if appropriation.budget_type != 'revenue':
            return {"error": "F4 report is only available for revenue type appropriations"}
        
        # Get appropriation lines
        lines = appropriation.line_ids
        
        # Build hierarchy: Budget Accounts → Lines (no Activity/Fund for revenue)
        hierarchy = self._build_hierarchy(lines)
        
        # Calculate totals
        total_amount = sum(line.balance for line in lines)
        
        return {
            "appropriation": {
                "id": appropriation.id,
                "name": appropriation.name,
                "date": appropriation.date.strftime("%d/%m/%Y") if appropriation.date else "",
                "state": appropriation.state,
                "total_amount": total_amount,
                "currency_symbol": appropriation.currency_id.symbol or "฿",
                "fiscal_year": {
                    "id": appropriation.date_range_fy_id.id,
                    "name": appropriation.date_range_fy_id.name,
                } if appropriation.date_range_fy_id else None,
                "department": {
                    "id": appropriation.department_analytic_id.id,
                    "name": appropriation.department_analytic_id.name,
                    "code": appropriation.department_analytic_id.code,
                    "complete_name": self._get_complete_name_without_codes(appropriation.department_analytic_id),
                } if appropriation.department_analytic_id else None,
                "source": {
                    "id": appropriation.source_analytic_id.id,
                    "name": appropriation.source_analytic_id.name,
                    "code": appropriation.source_analytic_id.code,
                } if appropriation.source_analytic_id else None,
                "journal": {
                    "id": appropriation.journal_id.id,
                    "name": appropriation.journal_id.name,
                } if appropriation.journal_id else None,
            },
            "hierarchy": hierarchy,
            "summary": {
                "total_lines": len(lines),
                "total_amount": total_amount,
                "accounts_count": len(hierarchy),
            }
        }

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
        
        if hasattr(record, 'complete_name') and record.complete_name:
            # Remove codes from complete_name
            import re
            return re.sub(r'\[.*?\]\s*', '', record.complete_name)
        return record.name