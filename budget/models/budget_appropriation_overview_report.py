import logging
from collections import defaultdict

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetAppropriationOverviewReport(models.TransientModel):
    _name = "budget.appropriation.overview.report"
    _description = "Budget Appropriation Overview Report"

    # Filter fields
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    fiscal_year_id = fields.Many2one('date.range', string="Fiscal Year",
                                     domain="[('type_id.fiscal_year', '=', True)]")
    department_ids = fields.Many2many('account.analytic.account',
                                      'budget_overview_dept_rel',
                                      'report_id', 'dept_id',
                                      string="Departments",
                                      domain="[('plan_id.code', '=', 'KTL_DEPARTMENT')]")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('all', 'All')
    ], string="State", default='all')

    @api.model
    def get_hierarchical_overview_data(self, filters):
        """Generate hierarchical data from multiple budget moves"""
        # Get filtered budget moves
        moves = self._get_filtered_moves(filters)

        if not moves:
            return {
                "filters": filters,
                "hierarchy": [],
                "summary": {
                    "total_amount": 0,
                    "move_count": 0,
                    "line_count": 0,
                    "fiscal_years": [],
                }
            }

        # Aggregate all non-virtual lines from these moves
        all_lines = self.env['budget.move.line']
        for move in moves:
            all_lines |= move.line_ids.filtered(lambda l: not l.is_virtual_line)

        # Build hierarchy using the existing logic from budget_appropriation_report
        hierarchy = self._build_aggregated_hierarchy(all_lines)

        # Get unique fiscal years
        fiscal_years = moves.mapped('date_range_fy_id')
        fiscal_year_names = ', '.join(fiscal_years.mapped('name'))

        return {
            "filters": filters,
            "hierarchy": hierarchy,
            "summary": {
                "total_amount": sum(line.balance for line in all_lines),
                "move_count": len(moves),
                "line_count": len(all_lines),
                "fiscal_years": fiscal_year_names,
            }
        }

    def _get_filtered_moves(self, filters):
        """Get budget moves based on filters"""
        domain = [('move_type', '=', 'appropriation')]

        # State filter
        state_filter = filters.get('state', 'all')
        if state_filter != 'all':
            domain.append(('state', '=', state_filter))

        # Date filters
        if filters.get('date_from'):
            domain.append(('date', '>=', filters['date_from']))
        if filters.get('date_to'):
            domain.append(('date', '<=', filters['date_to']))

        # Fiscal year filter
        if filters.get('fiscal_year_id'):
            domain.append(('date_range_fy_id', '=', filters['fiscal_year_id']))

        # Department filter
        if filters.get('department_ids'):
            domain.append(('department_analytic_id', 'in', filters['department_ids']))

        return self.env['budget.move'].search(domain, order='date desc')

    def _build_aggregated_hierarchy(self, lines):
        """Build hierarchy with aggregated data from multiple moves"""
        # Reuse the existing hierarchy building logic
        report_model = self.env['budget.appropriation.report']

        # Collect all unique analytic accounts and budget accounts
        all_analytic_ids = set()
        all_budget_account_ids = set()

        for line in lines:
            if line.activity_analytic_id:
                all_analytic_ids.add(line.activity_analytic_id.id)
            if line.department_analytic_id:
                all_analytic_ids.add(line.department_analytic_id.id)
            if line.fund_analytic_id:
                all_analytic_ids.add(line.fund_analytic_id.id)
            if line.account_id:
                all_budget_account_ids.add(line.account_id.id)

        # Get complete hierarchy paths
        hierarchy_paths = report_model._get_complete_hierarchy_paths(all_analytic_ids)
        budget_account_paths = report_model._get_budget_account_hierarchy_paths(all_budget_account_ids)

        # Build line data with paths
        line_data_with_paths = []

        for line in lines:
            paths = {
                'activity': report_model._get_path_hierarchy(line.activity_analytic_id, hierarchy_paths) if line.activity_analytic_id else [],
                'department': report_model._get_path_hierarchy(line.department_analytic_id, hierarchy_paths) if line.department_analytic_id else [],
                'fund': report_model._get_path_hierarchy(line.fund_analytic_id, hierarchy_paths) if line.fund_analytic_id else [],
            }

            budget_account_path = []
            if line.account_id and line.account_id.id in budget_account_paths:
                if line.account_id.parent_path:
                    path_ids = [int(id_str) for id_str in line.account_id.parent_path.strip('/').split('/') if id_str]
                    for account_id in path_ids:
                        if account_id in budget_account_paths:
                            budget_account_path.append(budget_account_paths[account_id])
                else:
                    budget_account_path.append(budget_account_paths[line.account_id.id])

            line_data = {
                "id": line.id,
                "move_id": line.move_id.id,
                "move_name": line.move_id.name,
                "account": {
                    "id": line.account_id.id,
                    "name": line.account_id.name,
                    "code": line.account_id.code,
                },
                "budget_account_path": budget_account_path,
                "balance": line.balance,
                "note": line.note or "",
                "analytic_distribution": line.analytic_distribution or {},
                "paths": paths
            }

            line_data_with_paths.append(line_data)

        # Build the hierarchy tree
        return report_model._build_tree_from_paths(line_data_with_paths, hide_department=False)

    @api.model
    def get_filter_options(self):
        """Get available options for filters"""
        # Get fiscal years that have budget appropriations
        fiscal_years = self.env['date.range'].search([
            ('type_id.fiscal_year', '=', True)
        ], order='date_start desc')

        # Get departments
        departments = self.env['account.analytic.account'].search([
            ('plan_id.code', '=', 'KTL_DEPARTMENT')
        ], order='name')

        return {
            'fiscal_years': [{
                'id': fy.id,
                'name': fy.name,
                'date_start': fy.date_start.strftime('%Y-%m-%d'),
                'date_end': fy.date_end.strftime('%Y-%m-%d'),
            } for fy in fiscal_years],
            'departments': [{
                'id': dept.id,
                'name': dept.name,
                'code': dept.code,
                'complete_name': dept.complete_name,
            } for dept in departments],
            'states': [
                {'value': 'draft', 'label': 'Draft'},
                {'value': 'posted', 'label': 'Posted'},
                {'value': 'all', 'label': 'All'},
            ]
        }
