import logging
import re

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SimpleTreeBuilder:
    """Simple tree builder for budget hierarchies"""
    
    def __init__(self):
        self.root = {'type': 'root', 'children': [], 'total_amount': 0}
        self.node_cache = {}
    
    def add_line(self, line):
        """Add a budget line to the hierarchy"""
        current = self.root
        
        # Build Activity hierarchy (global scope)
        if line.activity_analytic_id:
            path = self._get_record_path(line.activity_analytic_id, 'activity')
            current = self._build_dimension_path(current, 'activity', path, None)
        
        # Build Fund hierarchy (under current activity)
        if line.fund_analytic_id:
            path = self._get_record_path(line.fund_analytic_id, 'fund')
            parent_context = current.get('id')  # Current activity ID
            current = self._build_dimension_path(current, 'fund', path, parent_context)
        
        # Build Account hierarchy (under current fund)
        if line.account_id:
            path = self._get_record_path(line.account_id, 'account')
            parent_context = current.get('id')  # Current fund ID
            current = self._build_dimension_path(current, 'account', path, parent_context)
        
        # Add line data to leaf node
        self._add_line_data(current, line)
    
    def get_hierarchy(self):
        """Get final hierarchy with calculated totals"""
        self._calculate_totals(self.root)
        return self.root.get('children', [])
    
    def _get_record_path(self, record, dimension):
        """Get full path for record (works for both analytic and budget accounts)"""
        if not record:
            return []
        
        path = []
        current = record
        while current:
            path.insert(0, current)
            current = current.parent_id
        return path
    
    def _build_dimension_path(self, parent, dimension, records, parent_context):
        """Build path for a dimension (activity/fund/account)"""
        current = parent
        
        for record in records:
            # Create unique cache key
            cache_key = f"{dimension}_{record.id}"
            if parent_context:
                cache_key += f"_ctx_{parent_context}"
            
            # Find or create node
            if cache_key in self.node_cache:
                current = self.node_cache[cache_key]
            else:
                node = self._create_node(dimension, record, current)
                current['children'].append(node)
                self.node_cache[cache_key] = node
                current = node
        
        return current
    
    def _create_node(self, node_type, record, parent):
        """Create a new tree node"""
        return {
            'type': node_type,
            'key': f"{node_type}_{record.id}",
            'id': record.id,
            'name': record.name,
            'code': getattr(record, 'code', ''),
            'complete_name': self._clean_name(record),
            'children': [],
            'amount': 0,
            'total_amount': 0,
            'level': parent.get('level', -1) + 1,
            'has_data': False,
            'expanded': True,
            'line_details': []
        }
    
    def _add_line_data(self, node, line):
        """Add line data to leaf node"""
        node['amount'] = node.get('amount', 0) + line.balance
        node['has_data'] = True
        node['line_details'].append({
            'id': line.id,
            'note': line.note,
            'balance': line.balance
        })
    
    def _calculate_totals(self, node):
        """Calculate total amounts recursively"""
        if not node.get('children'):
            node['total_amount'] = node.get('amount', 0)
            return node['total_amount']
        
        total = node.get('amount', 0)
        for child in node['children']:
            total += self._calculate_totals(child)
        
        node['total_amount'] = total
        return total
    
    def _clean_name(self, record):
        """Get clean name without codes"""
        if not record:
            return ""
        
        if hasattr(record, 'complete_name') and record.complete_name:
            return re.sub(r'\[.*?\]\s*', '', record.complete_name)
        return record.name


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
                "activities_count": len(hierarchy),
            }
        }

    def _build_hierarchy(self, lines):
        """Build hierarchical tree structure: Activity → Fund → Account"""
        
        # Filter lines with non-zero balance
        lines = lines.filtered(lambda l: l.balance != 0)
        if not lines:
            return []
        
        # Initialize tree builder
        tree_builder = SimpleTreeBuilder()
        
        # Process each line and build hierarchy
        for line in lines:
            tree_builder.add_line(line)
        
        # Get completed tree and calculate totals
        return tree_builder.get_hierarchy()

