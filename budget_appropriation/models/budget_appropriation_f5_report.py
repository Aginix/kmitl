import logging

from odoo import api, fields, models, _

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
        
        # Create root node
        root = {
            'type': 'root',
            'name': 'Root',
            'children': [],
            'total_amount': 0
        }
        
        # Cache for node lookup
        node_cache = {}
        
        # Process each line
        for line in lines:
            current = root
            
            # 1. Build Activity hierarchy
            activity_path = self._get_hierarchy_path(line.activity_analytic_id)
            for activity in activity_path:
                current = self._ensure_node(
                    parent=current,
                    node_type='activity',
                    record=activity,
                    cache=node_cache,
                    context_key=None  # Activities are global
                )
            
            # 2. Build Fund hierarchy under activity
            fund_path = self._get_hierarchy_path(line.fund_analytic_id)
            for fund in fund_path:
                # Include activity context in cache key
                context_key = f"act_{current.get('id')}"
                current = self._ensure_node(
                    parent=current,
                    node_type='fund',
                    record=fund,
                    cache=node_cache,
                    context_key=context_key
                )
            
            # 3. Build Account hierarchy under fund
            account_path = self._get_account_hierarchy_path(line.account_id)
            for account in account_path:
                # Include fund context in cache key
                context_key = f"fund_{current.get('id')}"
                current = self._ensure_node(
                    parent=current,
                    node_type='account',
                    record=account,
                    cache=node_cache,
                    context_key=context_key
                )
            
            # 4. Add amount to leaf node
            current['amount'] = current.get('amount', 0) + line.balance
            current['has_data'] = True
            
            # Store line details for drill-down
            if 'line_details' not in current:
                current['line_details'] = []
            current['line_details'].append({
                'id': line.id,
                'note': line.note,
                'balance': line.balance
            })
        
        # Calculate rollups
        self._calculate_rollups(root)
        
        # Return children (skip root)
        return root.get('children', [])
    def _ensure_node(self, parent, node_type, record, cache, context_key=None):
        """Ensure node exists in tree"""
        
        # Build cache key
        cache_key = (node_type, record.id)
        if context_key:
            cache_key = (node_type, record.id, context_key)
        
        # Check cache
        if cache_key in cache:
            return cache[cache_key]
        
        # Create new node
        node = {
            'type': node_type,
            'key': f"{node_type}_{record.id}",
            'id': record.id,
            'name': record.name,
            'code': getattr(record, 'code', ''),
            'complete_name': self._get_complete_name_without_codes(record),
            'children': [],
            'amount': 0,
            'total_amount': 0,
            'level': parent.get('level', -1) + 1,
            'has_data': False,
            'expanded': True  # Default expanded
        }
        
        # Add to parent
        if 'children' not in parent:
            parent['children'] = []
        parent['children'].append(node)
        
        # Cache it
        cache[cache_key] = node
        
        return node
    
    def _get_hierarchy_path(self, analytic_account):
        """Get full hierarchy path for analytic account"""
        if not analytic_account:
            return []
            
        path = []
        current = analytic_account
        
        while current:
            path.insert(0, current)
            current = current.parent_id
            
        return path
    
    def _get_account_hierarchy_path(self, budget_account):
        """Get full hierarchy path for budget account"""
        if not budget_account:
            return []
            
        path = []
        current = budget_account
        
        while current:
            path.insert(0, current)
            current = current.parent_id
            
        return path
    
    def _calculate_rollups(self, node):
        """Calculate total amounts bottom-up"""
        
        # Leaf node - use direct amount
        if not node.get('children'):
            node['total_amount'] = node.get('amount', 0)
            return node['total_amount']
        
        # Branch node - sum children + own amount
        total = node.get('amount', 0)
        for child in node['children']:
            total += self._calculate_rollups(child)
        
        node['total_amount'] = total
        return total
    
    def _get_complete_name_without_codes(self, record):
        """Get complete name without codes"""
        if not record:
            return ""
        
        if hasattr(record, 'complete_name') and record.complete_name:
            # Remove codes from complete_name
            name = record.complete_name
            # Remove [code] patterns
            import re
            return re.sub(r'\[.*?\]\s*', '', name)
        return record.name

