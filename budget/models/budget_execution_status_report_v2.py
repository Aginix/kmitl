import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetExecutionStatusReportV2(models.TransientModel):
    """Simplified Budget Execution Status Report V2"""
    _inherit = "budget.execution.status.report"

    @api.model
    def get_report_data(self, filters=None):
        """Get report data with minimal processing"""
        if not filters:
            filters = {}
            
        # Get budget moves data
        budget_data = self._get_budget_data(filters)
        
        # Build simple hierarchical structure
        hierarchical_data = self._build_hierarchy(budget_data)
        
        # Calculate summary
        summary = self._calculate_summary(hierarchical_data)
        
        return {
            'hierarchical_data': hierarchical_data,
            'summary': summary,
            'filters': filters
        }
    
    def _get_budget_data(self, filters):
        """Get budget data with simple aggregation"""
        domain = [('state', '=', 'posted')]
        
        # Apply basic filters
        if filters.get('date_from'):
            domain.append(('date', '>=', filters['date_from']))
        if filters.get('date_to'):
            domain.append(('date', '<=', filters['date_to']))
        if filters.get('date_range_fy_id'):
            domain.append(('date_range_fy_id', '=', filters['date_range_fy_id']))
            
        # Get budget move lines
        move_lines = self.env['budget.move.line'].search_read(
            domain=domain,
            fields=['account_id', 'activity_analytic_id', 'balance', 'move_id']
        )
        
        # Simple aggregation by account and activity
        data = {}
        for line in move_lines:
            # Get move type
            move = self.env['budget.move'].browse(line['move_id'][0])
            move_type = move.move_type
            
            # Create key
            account_id = line['account_id'][0] if line['account_id'] else 0
            activity_id = line['activity_analytic_id'][0] if line['activity_analytic_id'] else 0
            key = (account_id, activity_id)
            
            # Initialize if needed
            if key not in data:
                data[key] = {
                    'account_id': account_id,
                    'account_name': line['account_id'][1] if line['account_id'] else 'No Account',
                    'activity_id': activity_id,
                    'activity_name': line['activity_analytic_id'][1] if line['activity_analytic_id'] else 'No Activity',
                    'appropriation': 0,
                    'consumed': 0,
                    'remaining': 0
                }
            
            # Aggregate amounts
            amount = abs(line['balance'])
            if move_type == 'appropriation':
                data[key]['appropriation'] += amount
            elif move_type == 'consume':
                data[key]['consumed'] += amount
                
        # Calculate remaining
        for item in data.values():
            item['remaining'] = item['appropriation'] - item['consumed']
            item['utilization'] = (item['consumed'] / item['appropriation'] * 100) if item['appropriation'] > 0 else 0
            
        return list(data.values())
    
    def _build_hierarchy(self, data):
        """Build simple two-level hierarchy: Account -> Activity"""
        hierarchy = {}
        
        for item in data:
            account_id = item['account_id']
            
            # Create account node if not exists
            if account_id not in hierarchy:
                hierarchy[account_id] = {
                    'id': f'account_{account_id}',
                    'name': item['account_name'],
                    'type': 'account',
                    'appropriation': 0,
                    'consumed': 0,
                    'remaining': 0,
                    'children': []
                }
            
            # Add to account totals
            account_node = hierarchy[account_id]
            account_node['appropriation'] += item['appropriation']
            account_node['consumed'] += item['consumed']
            account_node['remaining'] += item['remaining']
            
            # Add activity as child
            if item['activity_id']:
                activity_node = {
                    'id': f'activity_{item["activity_id"]}_{account_id}',
                    'name': item['activity_name'],
                    'type': 'activity',
                    'appropriation': item['appropriation'],
                    'consumed': item['consumed'],
                    'remaining': item['remaining'],
                    'utilization': item['utilization']
                }
                account_node['children'].append(activity_node)
        
        # Calculate utilization for accounts
        for account in hierarchy.values():
            account['utilization'] = (account['consumed'] / account['appropriation'] * 100) if account['appropriation'] > 0 else 0
            
        return list(hierarchy.values())
    
    def _calculate_summary(self, hierarchical_data):
        """Calculate simple summary totals"""
        summary = {
            'total_appropriation': 0,
            'total_consumed': 0,
            'total_remaining': 0,
            'total_utilization': 0
        }
        
        # Sum top-level nodes only
        for node in hierarchical_data:
            summary['total_appropriation'] += node['appropriation']
            summary['total_consumed'] += node['consumed']
            summary['total_remaining'] += node['remaining']
            
        # Calculate overall utilization
        if summary['total_appropriation'] > 0:
            summary['total_utilization'] = (summary['total_consumed'] / summary['total_appropriation'] * 100)
            
        return summary
    
    @api.model
    def get_filter_options(self):
        """Get available filter options"""
        # Get fiscal years
        fiscal_years = self.env['date.range'].search_read(
            domain=[('type_name', '=', 'ปีงบประมาณ')],
            fields=['id', 'name', 'date_start', 'date_end'],
            order='date_start desc',
            limit=5
        )
        
        # Mark current fiscal year
        today = fields.Date.today()
        for fy in fiscal_years:
            fy['is_current'] = fy['date_start'] <= today <= fy['date_end']
            
        return {
            'fiscal_years': fiscal_years
        }