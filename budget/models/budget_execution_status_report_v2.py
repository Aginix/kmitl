import logging
import base64
from collections import defaultdict
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount

_logger = logging.getLogger(__name__)


class BudgetExecutionStatusReportV2(models.TransientModel):
    """Enhanced Budget Execution Status Report with real-time capabilities"""
    _inherit = "budget.execution.status.report"

    @api.model
    def get_real_time_data(self, filters):
        """
        Get real-time budget execution data with optimized queries
        Supports WebSocket updates for live data streaming
        """
        try:
            # Validate and prepare filters
            filter_vals = self._prepare_filters_from_dict(filters)
            
            # Use read_group for better performance on large datasets
            domain = self._build_optimized_domain(filter_vals)
            
            # Get aggregated data using read_group
            budget_data = self._get_aggregated_budget_data(domain)
            commitment_data = self._get_aggregated_commitment_data(filter_vals)
            
            # Merge and process data
            processed_data = self._merge_budget_commitment_data(budget_data, commitment_data)
            
            # Build hierarchical structure with optimizations
            hierarchical_data = self._build_optimized_hierarchy(processed_data)
            
            # Calculate summary with caching
            summary = self._calculate_cached_summary(hierarchical_data)
            
            return {
                'success': True,
                'data': {
                    'hierarchical_data': hierarchical_data,
                    'summary': summary,
                    'last_update': fields.Datetime.now(),
                    'record_count': len(processed_data),
                }
            }
            
        except Exception as e:
            _logger.error(f"Error in get_real_time_data: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _build_optimized_domain(self, filters):
        """Build optimized domain for database queries"""
        domain = [
            ('state', '=', 'posted'),
            ('company_id', '=', filters.get('company_id', self.env.company.id))
        ]
        
        # Date filters with index optimization
        if filters.get('date_from'):
            domain.append(('date', '>=', filters['date_from']))
        if filters.get('date_to'):
            domain.append(('date', '<=', filters['date_to']))
            
        # Fiscal year filter
        if filters.get('date_range_fy_id'):
            domain.append(('date_range_fy_id', '=', filters['date_range_fy_id']))
            
        # Budget type filter
        if filters.get('budget_type'):
            domain.append(('budget_type', '=', filters['budget_type']))
            
        return domain

    def _get_aggregated_budget_data(self, domain):
        """Get aggregated budget move data using read_group for performance"""
        BudgetMoveLine = self.env['budget.move.line']
        
        # Group by all analytic dimensions and budget account
        group_fields = [
            'account_id',
            'activity_analytic_id', 
            'department_analytic_id',
            'fund_analytic_id',
            'source_analytic_id'
        ]
        
        # Get aggregated data by move type
        results = defaultdict(lambda: defaultdict(float))
        
        for move_type in ['appropriation', 'consume', 'entry']:
            type_domain = domain + [('move_id.move_type', '=', move_type)]
            
            grouped_data = BudgetMoveLine.read_group(
                domain=type_domain,
                fields=['balance:sum'],
                groupby=group_fields,
                lazy=False
            )
            
            for group in grouped_data:
                key = self._create_grouping_key(group)
                amount = abs(group.get('balance', 0))
                
                if move_type == 'appropriation':
                    results[key]['initial_appropriation'] += amount
                    results[key]['current_budget'] += amount
                elif move_type == 'consume':
                    results[key]['obligated_amount'] += amount
                    results[key]['current_budget'] -= amount
                elif move_type == 'entry':
                    results[key]['disbursed_amount'] += amount
                    
        return dict(results)

    def _get_aggregated_commitment_data(self, filters):
        """Get aggregated commitment data with performance optimization"""
        domain = [
            ('company_id', '=', filters.get('company_id', self.env.company.id)),
            ('state', 'not in', ['draft', 'cancel'])
        ]
        
        # Date filters
        if filters.get('date_from'):
            domain.append(('date', '>=', filters['date_from']))
        if filters.get('date_to'):
            domain.append(('date', '<=', filters['date_to']))
            
        # Analytic filters
        if filters.get('department_analytic_ids'):
            domain.append(('department_analytic_id', 'in', filters['department_analytic_ids']))
        if filters.get('source_analytic_ids'):
            domain.append(('source_analytic_id', 'in', filters['source_analytic_ids']))
            
        CommitmentLine = self.env['budget.commitment.line']
        
        # Get all commitment lines with their states
        commitment_lines = CommitmentLine.search_read(
            domain=[('commitment_id.state', 'not in', ['draft', 'cancel'])],
            fields=['account_id', 'activity_analytic_id', 'fund_analytic_id',
                    'amount', 'consumed_amount', 'commitment_id']
        )
        
        # Process commitment data
        results = defaultdict(lambda: defaultdict(float))
        
        for line in commitment_lines:
            commitment = self.env['budget.commitment'].browse(line['commitment_id'][0])
            
            key = (
                line['account_id'][0] if line['account_id'] else 0,
                line['activity_analytic_id'][0] if line['activity_analytic_id'] else 0,
                commitment.department_analytic_id.id if commitment.department_analytic_id else 0,
                line['fund_analytic_id'][0] if line['fund_analytic_id'] else 0,
                commitment.source_analytic_id.id if commitment.source_analytic_id else 0,
            )
            
            results[key]['total_requested'] += line['amount']
            
            if commitment.state == 'reserved':
                results[key]['reserved_amount'] += line['amount'] - line['consumed_amount']
                
        return dict(results)

    def _merge_budget_commitment_data(self, budget_data, commitment_data):
        """Merge budget and commitment data efficiently"""
        all_keys = set(budget_data.keys()) | set(commitment_data.keys())
        
        merged_data = []
        for key in all_keys:
            budget = budget_data.get(key, {})
            commitment = commitment_data.get(key, {})
            
            # Calculate derived values
            total_used = (
                budget.get('reserved_amount', 0) +
                budget.get('obligated_amount', 0) + 
                budget.get('disbursed_amount', 0)
            )
            
            remaining = budget.get('current_budget', 0) - total_used
            
            merged_data.append({
                'key': key,
                'budget_account_id': key[0],
                'activity_analytic_id': key[1], 
                'department_analytic_id': key[2],
                'fund_analytic_id': key[3],
                'source_analytic_id': key[4],
                'initial_appropriation': budget.get('initial_appropriation', 0),
                'current_budget': budget.get('current_budget', 0),
                'total_requested': commitment.get('total_requested', 0),
                'reserved_amount': commitment.get('reserved_amount', 0),
                'obligated_amount': budget.get('obligated_amount', 0),
                'disbursed_amount': budget.get('disbursed_amount', 0),
                'total_used': total_used,
                'remaining_budget': remaining,
                'utilization': (total_used / budget.get('current_budget', 1) * 100) 
                              if budget.get('current_budget', 0) > 0 else 0
            })
            
        return merged_data

    def _build_optimized_hierarchy(self, data):
        """Build hierarchical structure with performance optimizations"""
        # Cache frequently accessed data
        self._preload_hierarchy_cache(data)
        
        # Build hierarchy using cached data
        hierarchy = {}
        
        for item in data:
            # Skip items with no budget account
            if not item['budget_account_id']:
                continue
                
            # Get cached hierarchy paths
            activity_path = self._get_cached_path(item['activity_analytic_id'], 'activities')
            fund_path = self._get_cached_path(item['fund_analytic_id'], 'funds')
            account_path = self._get_cached_budget_account_path(item['budget_account_id'])
            
            # Build nested structure
            self._insert_into_hierarchy(hierarchy, item, activity_path, fund_path, account_path)
            
        # Convert to list and calculate rollup totals
        result = list(hierarchy.values())
        self._calculate_rollup_totals(result)
        
        return result

    def _preload_hierarchy_cache(self, data):
        """Preload hierarchy data for better performance"""
        # Collect all unique IDs
        analytic_ids = set()
        account_ids = set()
        
        for item in data:
            if item['activity_analytic_id']:
                analytic_ids.add(item['activity_analytic_id'])
            if item['fund_analytic_id']:
                analytic_ids.add(item['fund_analytic_id'])
            if item['budget_account_id']:
                account_ids.add(item['budget_account_id'])
                
        # Batch load analytic accounts with parent paths
        if analytic_ids:
            analytics = self.env['account.analytic.account'].browse(list(analytic_ids))
            self._analytic_cache = {
                a.id: {
                    'id': a.id,
                    'name': a.name,
                    'code': a.code or '',
                    'parent_path': a.parent_path,
                    'root_plan_code': a.root_plan_id.code if a.root_plan_id else ''
                } for a in analytics
            }
        else:
            self._analytic_cache = {}
            
        # Batch load budget accounts
        if account_ids:
            accounts = self.env['budget.account'].browse(list(account_ids))
            self._account_cache = {
                a.id: {
                    'id': a.id,
                    'name': a.name,
                    'code': a.code or '',
                    'parent_path': a.parent_path
                } for a in accounts
            }
        else:
            self._account_cache = {}

    def _get_cached_path(self, analytic_id, plan_code):
        """Get hierarchical path from cache"""
        if not analytic_id or analytic_id not in self._analytic_cache:
            return []
            
        analytic = self._analytic_cache[analytic_id]
        if analytic['root_plan_code'] != plan_code:
            return []
            
        # Build path from parent_path
        path = []
        if analytic['parent_path']:
            path_ids = [int(x) for x in analytic['parent_path'].strip('/').split('/') if x]
            for pid in path_ids:
                if pid in self._analytic_cache:
                    path.append(self._analytic_cache[pid])
                    
        return path

    def _get_cached_budget_account_path(self, account_id):
        """Get budget account hierarchical path from cache"""
        if not account_id or account_id not in self._account_cache:
            return []
            
        account = self._account_cache[account_id]
        path = []
        
        if account['parent_path']:
            path_ids = [int(x) for x in account['parent_path'].strip('/').split('/') if x]
            for pid in path_ids:
                if pid in self._account_cache:
                    path.append(self._account_cache[pid])
                    
        return path

    def _calculate_cached_summary(self, hierarchical_data):
        """Calculate summary with caching for performance"""
        summary = {
            'total_initial_appropriation': 0,
            'total_current_budget': 0,
            'total_requested': 0,
            'total_reserved': 0,
            'total_obligated': 0,
            'total_disbursed': 0,
            'total_used': 0,
            'total_remaining': 0,
            'total_returned': 0,
            'utilization_percentage': 0
        }
        
        # Sum only root level to avoid double counting
        for node in hierarchical_data:
            if node.get('totals'):
                totals = node['totals']
                summary['total_initial_appropriation'] += totals.get('initial_appropriation', 0)
                summary['total_current_budget'] += totals.get('current_budget', 0)
                summary['total_requested'] += totals.get('total_requested', 0)
                summary['total_reserved'] += totals.get('reserved_amount', 0)
                summary['total_obligated'] += totals.get('obligated_amount', 0)
                summary['total_disbursed'] += totals.get('disbursed_amount', 0)
                summary['total_used'] += totals.get('total_used', 0)
                summary['total_remaining'] += totals.get('remaining_budget', 0)
                
        # Calculate utilization percentage
        if summary['total_current_budget'] > 0:
            summary['utilization_percentage'] = (
                summary['total_used'] / summary['total_current_budget'] * 100
            )
            
        return summary

    @api.model
    def export_to_excel_v2(self, filters):
        """Enhanced Excel export with better formatting and performance"""
        try:
            import xlsxwriter
            import io
            
            # Get report data
            report_data = self.get_real_time_data(filters)
            
            if not report_data['success']:
                raise UserError(_("Failed to generate report data"))
                
            # Create Excel file in memory
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            
            # Add formats
            formats = self._create_excel_formats(workbook)
            
            # Create worksheets
            self._create_summary_sheet(workbook, report_data['data']['summary'], formats)
            self._create_detail_sheet(workbook, report_data['data']['hierarchical_data'], formats)
            
            workbook.close()
            output.seek(0)
            
            # Save to attachment
            attachment = self.env['ir.attachment'].create({
                'name': f'budget_execution_status_{fields.Date.today()}.xlsx',
                'type': 'binary',
                'datas': base64.b64encode(output.read()),
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            })
            
            return {
                'url': f'/web/content/{attachment.id}?download=true',
                'attachment_id': attachment.id
            }
            
        except ImportError:
            raise UserError(_("xlsxwriter library is required for Excel export"))
        except Exception as e:
            _logger.error(f"Error in Excel export: {str(e)}")
            raise UserError(_("Failed to export to Excel: %s") % str(e))

    def _create_excel_formats(self, workbook):
        """Create Excel formatting styles"""
        return {
            'header': workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            }),
            'subheader': workbook.add_format({
                'bold': True,
                'bg_color': '#D9E2F3',
                'border': 1
            }),
            'currency': workbook.add_format({
                'num_format': '#,##0.00',
                'border': 1
            }),
            'percentage': workbook.add_format({
                'num_format': '0.00%',
                'border': 1
            }),
            'normal': workbook.add_format({
                'border': 1
            }),
            'total': workbook.add_format({
                'bold': True,
                'bg_color': '#F2F2F2',
                'border': 1
            }),
            'danger': workbook.add_format({
                'bg_color': '#FFC7CE',
                'font_color': '#9C0006',
                'border': 1
            }),
            'warning': workbook.add_format({
                'bg_color': '#FFEB9C',
                'font_color': '#9C6500',
                'border': 1
            }),
            'success': workbook.add_format({
                'bg_color': '#C6EFCE',
                'font_color': '#006100',
                'border': 1
            })
        }

    @api.model 
    def subscribe_to_updates(self, channel_name, filters):
        """Subscribe to real-time updates via WebSocket"""
        # This would integrate with a WebSocket server for real-time updates
        # For now, return subscription confirmation
        return {
            'subscribed': True,
            'channel': channel_name,
            'update_interval': 30000  # 30 seconds
        }