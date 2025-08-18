import logging

from odoo import api, fields, models, _
from ..utils.tree_builder import BudgetTreeBuilder, TreeConfig, BudgetTreeExporter

_logger = logging.getLogger(__name__)


class BudgetAppropriationF5Overview(models.TransientModel):
    _name = "budget.appropriation.f5.overview"
    _description = "Budget Appropriation F5 Overview Report"

    # Filter Fields
    fiscal_year_id = fields.Many2one(
        "date.range", 
        string="Fiscal Year", 
        help="Filter by fiscal year"
    )
    department_ids = fields.Many2many(
        "account.analytic.account",
        "f5_overview_department_rel", 
        "overview_id", 
        "department_id",
        string="Departments",
        domain=[("root_plan_id.code", "=", "departments")],
        help="Filter by departments (leave empty for all)"
    )
    activity_ids = fields.Many2many(
        "account.analytic.account",
        "f5_overview_activity_rel",
        "overview_id", 
        "activity_id", 
        string="Activities",
        domain=[("root_plan_id.code", "=", "activities")],
        help="Filter by activities (leave empty for all)"
    )
    fund_ids = fields.Many2many(
        "account.analytic.account",
        "f5_overview_fund_rel",
        "overview_id", 
        "fund_id",
        string="Funds", 
        domain=[("root_plan_id.code", "=", "funds")],
        help="Filter by funds (leave empty for all)"
    )
    source_ids = fields.Many2many(
        "account.analytic.account",
        "f5_overview_source_rel",
        "overview_id", 
        "source_id",
        string="Sources",
        domain=[("root_plan_id.code", "=", "sources")],
        help="Filter by sources (leave empty for all)"
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'), 
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], string="State", help="Filter by appropriation state (leave empty for all)")
    
    include_zero_amounts = fields.Boolean(
        string="Include Zero Amounts",
        default=False,
        help="Include lines with zero balance"
    )

    @api.model
    def get_f5_overview_data(self, options=None):
        """Generate F5 overview data for all budget appropriations"""
        if options is None:
            options = {}
        
        # Get filtered appropriations
        appropriations = self._get_filtered_appropriations(options)
        
        if not appropriations:
            return {
                "appropriations_summary": {
                    "total_count": 0,
                    "total_amount": 0.0,
                    "by_state": {},
                    "currency_symbol": "฿"
                },
                "hierarchy": [],
                "summary": {
                    "total_lines": 0,
                    "total_amount": 0.0,
                    "activities_count": 0,
                    "appropriations_count": 0
                }
            }
        
        # Get all lines from filtered appropriations
        all_lines = appropriations.mapped('line_ids')
        
        # Build hierarchy using TreeBuilder
        hierarchy = self._build_overview_hierarchy(all_lines, options)
        
        # Calculate totals
        total_amount = sum(line.balance for line in all_lines)
        
        # Generate appropriations summary
        appropriations_summary = self._generate_appropriations_summary(appropriations)
        
        return {
            "appropriations_summary": appropriations_summary,
            "hierarchy": hierarchy,
            "summary": {
                "total_lines": len(all_lines),
                "total_amount": total_amount,
                "activities_count": len(hierarchy),
                "appropriations_count": len(appropriations),
                "departments_count": len(appropriations.mapped('department_analytic_id')),
                "funds_count": len(all_lines.mapped('fund_analytic_id')),
                "date_range": self._get_date_range_summary(appropriations)
            }
        }

    def _get_filtered_appropriations(self, options):
        """Get appropriations based on filter criteria"""
        domain = [('budget_type', '=', 'expense')]  # F5 is for expenses only
        
        # Apply filters from options
        fiscal_year_id = options.get('fiscal_year_id')
        if fiscal_year_id:
            domain.append(('date_range_fy_id', '=', fiscal_year_id))
        
        department_ids = options.get('department_ids', [])
        if department_ids:
            domain.append(('department_analytic_id', 'in', department_ids))
        
        activity_ids = options.get('activity_ids', [])
        if activity_ids:
            # Get appropriations that have lines with these activities
            lines_with_activities = self.env['budget.appropriation.line'].search([
                ('activity_analytic_id', 'in', activity_ids)
            ])
            appropriation_ids = lines_with_activities.mapped('appropriation_id.id')
            if appropriation_ids:
                domain.append(('id', 'in', appropriation_ids))
            else:
                domain.append(('id', '=', False))  # No matching appropriations
        
        fund_ids = options.get('fund_ids', [])
        if fund_ids:
            # Get appropriations that have lines with these funds
            lines_with_funds = self.env['budget.appropriation.line'].search([
                ('fund_analytic_id', 'in', fund_ids)
            ])
            appropriation_ids = lines_with_funds.mapped('appropriation_id.id')
            if appropriation_ids:
                domain.append(('id', 'in', appropriation_ids))
            else:
                domain.append(('id', '=', False))  # No matching appropriations
        
        source_ids = options.get('source_ids', [])
        if source_ids:
            # Get appropriations that have lines with these sources
            lines_with_sources = self.env['budget.appropriation.line'].search([
                ('source_analytic_id', 'in', source_ids)
            ])
            appropriation_ids = lines_with_sources.mapped('appropriation_id.id')
            if appropriation_ids:
                domain.append(('id', 'in', appropriation_ids))
            else:
                domain.append(('id', '=', False))  # No matching appropriations
        
        state = options.get('state')
        if state:
            domain.append(('state', '=', state))
        
        return self.env['budget.appropriation'].search(domain)

    def _build_overview_hierarchy(self, lines, options):
        """Build hierarchy for overview using TreeBuilder"""
        if not lines:
            return []
        
        # Configure tree builder for overview
        config = TreeConfig(
            dimensions=['activity', 'fund', 'account'],
            include_empty=options.get('include_zero_amounts', False),
            calculate_rollups=True,
            amount_field='balance'
        )
        
        # Apply additional filters to lines if needed
        filtered_lines = lines
        
        # Filter by specific fund/source/activity IDs at line level
        fund_ids = options.get('fund_ids', [])
        if fund_ids:
            filtered_lines = filtered_lines.filtered(
                lambda l: l.fund_analytic_id.id in fund_ids
            )
        
        source_ids = options.get('source_ids', [])
        if source_ids:
            filtered_lines = filtered_lines.filtered(
                lambda l: l.source_analytic_id.id in source_ids
            )
        
        activity_ids = options.get('activity_ids', [])
        if activity_ids:
            filtered_lines = filtered_lines.filtered(
                lambda l: l.activity_analytic_id.id in activity_ids
            )
        
        # Build tree
        tree_builder = BudgetTreeBuilder(config)
        tree = tree_builder.build_tree(filtered_lines)
        
        # Export to Odoo-compatible format
        return BudgetTreeExporter.to_odoo_hierarchy(tree)

    def _generate_appropriations_summary(self, appropriations):
        """Generate summary of appropriations"""
        if not appropriations:
            return {
                "total_count": 0,
                "total_amount": 0.0,
                "by_state": {},
                "currency_symbol": "฿"
            }
        
        # Count by state
        by_state = {}
        for state in ['draft', 'review', 'posted', 'cancel']:
            count = len(appropriations.filtered(lambda a: a.state == state))
            if count > 0:
                by_state[state] = count
        
        # Calculate total amount
        total_amount = sum(appropriation.amount_total for appropriation in appropriations)
        
        # Get currency symbol (assume all same currency)
        currency_symbol = appropriations[0].currency_id.symbol if appropriations else "฿"
        
        return {
            "total_count": len(appropriations),
            "total_amount": total_amount,
            "by_state": by_state,
            "currency_symbol": currency_symbol,
            "departments": list(set(appropriations.mapped('department_analytic_id.name'))),
            "fiscal_years": list(set(appropriations.mapped('date_range_fy_id.name')))
        }

    def _get_date_range_summary(self, appropriations):
        """Get date range summary from appropriations"""
        if not appropriations:
            return {}
        
        dates = appropriations.mapped('date')
        dates = [d for d in dates if d]  # Filter out None dates
        
        if not dates:
            return {}
        
        return {
            "earliest": min(dates).strftime("%d/%m/%Y"),
            "latest": max(dates).strftime("%d/%m/%Y"),
            "count": len(dates)
        }

    @api.model
    def get_default_filters(self):
        """Get default filter values"""
        # Get current fiscal year if available
        current_fy = self.env['date.range'].search([
            ('name', 'ilike', '2024')  # Simple fallback - can be improved later
        ], limit=1, order='date_start desc')
        
        return {
            'fiscal_year_id': current_fy.id if current_fy else False,
            'department_ids': [],
            'activity_ids': [],
            'fund_ids': [],
            'source_ids': [],
            'state': False,
            'include_zero_amounts': False
        }

    def action_generate_overview(self):
        """Action to generate overview report"""
        options = {
            'fiscal_year_id': self.fiscal_year_id.id if self.fiscal_year_id else False,
            'department_ids': self.department_ids.ids,
            'activity_ids': self.activity_ids.ids,
            'fund_ids': self.fund_ids.ids,
            'source_ids': self.source_ids.ids,
            'state': self.state,
            'include_zero_amounts': self.include_zero_amounts
        }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'budget_appropriation_f5_overview',
            'context': {
                'overview_options': options,
                'overview_id': self.id
            }
        }