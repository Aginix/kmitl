import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetReportLine(models.TransientModel):
    _name = "budget.report.line"
    _description = "Budget Report Line"
    _order = "report_id, level, sequence, name"

    report_id = fields.Many2one(
        comodel_name="budget.report",
        string="Budget Report",
        required=True,
        index=True,
        ondelete="cascade",
    )
    
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Sequence for ordering lines",
    )
    
    name = fields.Char(
        string="Name",
        required=True,
        help="Display name for this report line",
    )
    
    code = fields.Char(
        string="Code",
        help="Code for sorting and identification",
    )
    
    level = fields.Integer(
        string="Level",
        default=0,
        help="Hierarchy level (0=root, 1=child, etc.)",
    )
    
    parent_id = fields.Many2one(
        comodel_name="budget.report.line",
        string="Parent Line",
        help="Parent line for hierarchical structure",
    )
    
    child_ids = fields.One2many(
        comodel_name="budget.report.line",
        inverse_name="parent_id",
        string="Child Lines",
    )
    
    group_key = fields.Char(
        string="Group Key",
        help="Key used for grouping data",
    )
    
    line_type = fields.Selection(
        selection=[
            ("header", "Header"),
            ("detail", "Detail"),
            ("total", "Total"),
            ("subtotal", "Subtotal"),
        ],
        string="Line Type",
        default="detail",
        help="Type of report line",
    )
    
    # Financial Data
    budget_amount = fields.Monetary(
        string="Budget Amount",
        currency_field="currency_id",
        help="Allocated budget amount",
    )
    
    actual_amount = fields.Monetary(
        string="Actual Amount", 
        currency_field="currency_id",
        help="Actual spent amount",
    )
    
    commitment_amount = fields.Monetary(
        string="Commitment Amount",
        currency_field="currency_id", 
        help="Committed but not yet spent amount",
    )
    
    available_amount = fields.Monetary(
        string="Available Amount",
        currency_field="currency_id",
        help="Available for spending (Budget - Actual - Commitment)",
    )
    
    variance_amount = fields.Monetary(
        string="Variance Amount",
        compute="_compute_variance",
        currency_field="currency_id",
        help="Budget vs Actual variance",
    )
    
    variance_percentage = fields.Float(
        string="Variance %",
        compute="_compute_variance",
        help="Variance as percentage of budget",
    )
    
    utilization_percentage = fields.Float(
        string="Utilization %",
        compute="_compute_utilization",
        help="Actual utilization percentage of budget",
    )
    
    # Analytic Dimensions (for filtering and grouping)
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        domain=[("root_plan_id.code", "=", "activities")],
    )
    
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department", 
        domain=[("root_plan_id.code", "=", "departments")],
    )
    
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        domain=[("root_plan_id.code", "=", "funds")],
    )
    
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        domain=[("root_plan_id.code", "=", "sources")],
    )
    
    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
    )
    
    # Related fields
    currency_id = fields.Many2one(
        related="report_id.currency_id",
        string="Currency",
    )
    
    company_id = fields.Many2one(
        related="report_id.company_id",
        string="Company",
    )
    
    # Display control
    is_bold = fields.Boolean(
        string="Bold",
        default=False,
        help="Display line in bold",
    )
    
    is_total_line = fields.Boolean(
        string="Is Total Line",
        default=False,
        help="Mark as total line for styling",
    )
    
    show_details = fields.Boolean(
        string="Show Details",
        default=True,
        help="Show detailed breakdown",
    )
    
    # Statistical data
    count_budget_moves = fields.Integer(
        string="Budget Moves Count",
        help="Number of budget moves contributing to this line",
    )
    
    count_commitments = fields.Integer(
        string="Commitments Count",
        help="Number of commitments contributing to this line",
    )
    
    notes = fields.Text(
        string="Notes",
        help="Additional notes for this line",
    )
    
    @api.depends("budget_amount", "actual_amount")
    def _compute_variance(self):
        """Calculate variance between budget and actual"""
        for line in self:
            line.variance_amount = line.budget_amount - line.actual_amount
            
            if line.budget_amount != 0:
                line.variance_percentage = (line.variance_amount / line.budget_amount) * 100
            else:
                line.variance_percentage = 0.0
    
    @api.depends("budget_amount", "actual_amount")
    def _compute_utilization(self):
        """Calculate utilization percentage"""
        for line in self:
            if line.budget_amount != 0:
                line.utilization_percentage = (line.actual_amount / line.budget_amount) * 100
            else:
                line.utilization_percentage = 0.0 if line.actual_amount == 0 else 100.0
    
    def name_get(self):
        """Custom name display with hierarchy indication"""
        result = []
        for line in self:
            name = line.name
            if line.level > 0:
                name = "  " * line.level + name
            if line.code:
                name = f"[{line.code}] {name}"
            result.append((line.id, name))
        return result
    
    @api.model
    def create_header_line(self, report_id, name, level=0, parent_id=None):
        """Helper method to create header lines"""
        return self.create({
            'report_id': report_id,
            'name': name,
            'level': level,
            'parent_id': parent_id,
            'line_type': 'header',
            'is_bold': True,
            'show_details': False,
        })
    
    @api.model
    def create_total_line(self, report_id, name, amounts, level=0, parent_id=None):
        """Helper method to create total lines"""
        return self.create({
            'report_id': report_id,
            'name': name,
            'level': level,
            'parent_id': parent_id,
            'line_type': 'total',
            'is_bold': True,
            'is_total_line': True,
            'budget_amount': amounts.get('budget', 0.0),
            'actual_amount': amounts.get('actual', 0.0),
            'commitment_amount': amounts.get('commitment', 0.0),
            'available_amount': amounts.get('available', 0.0),
        })
    
    def action_drill_down(self):
        """Drill down to detailed view of this line"""
        self.ensure_one()
        
        # Build action to show detailed breakdown
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Budget Details: %s') % self.name,
            'res_model': 'budget.move.line',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {
                'default_activity_analytic_id': self.activity_analytic_id.id,
                'default_department_analytic_id': self.department_analytic_id.id,
                'default_fund_analytic_id': self.fund_analytic_id.id,
                'default_source_analytic_id': self.source_analytic_id.id,
                'default_account_id': self.budget_account_id.id,
            }
        }
        
        # Build domain for filtering
        domain = []
        
        if self.activity_analytic_id:
            domain.append(('activity_analytic_id', '=', self.activity_analytic_id.id))
        if self.department_analytic_id:
            domain.append(('department_analytic_id', '=', self.department_analytic_id.id))
        if self.fund_analytic_id:
            domain.append(('fund_analytic_id', '=', self.fund_analytic_id.id))
        if self.source_analytic_id:
            domain.append(('source_analytic_id', '=', self.source_analytic_id.id))
        if self.budget_account_id:
            domain.append(('account_id', '=', self.budget_account_id.id))
        
        # Add date filters from parent report
        if self.report_id.date_from:
            domain.append(('date', '>=', self.report_id.date_from))
        if self.report_id.date_to:
            domain.append(('date', '<=', self.report_id.date_to))
        
        action['domain'] = domain
        return action
    
    def action_view_commitments(self):
        """Show commitments related to this line"""
        self.ensure_one()
        
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Commitments: %s') % self.name,
            'res_model': 'budget.commitment.line',
            'view_mode': 'tree,form',
            'target': 'current',
        }
        
        # Build domain for commitment filtering
        domain = []
        
        if self.activity_analytic_id:
            domain.append(('activity_analytic_id', '=', self.activity_analytic_id.id))
        if self.department_analytic_id:
            domain.append(('department_analytic_id', '=', self.department_analytic_id.id))
        if self.fund_analytic_id:
            domain.append(('fund_analytic_id', '=', self.fund_analytic_id.id))
        if self.source_analytic_id:
            domain.append(('source_analytic_id', '=', self.source_analytic_id.id))
        if self.budget_account_id:
            domain.append(('account_id', '=', self.budget_account_id.id))
        
        # Add date filters
        if self.report_id.date_from:
            domain.append(('date', '>=', self.report_id.date_from))
        if self.report_id.date_to:
            domain.append(('date', '<=', self.report_id.date_to))
        
        action['domain'] = domain
        return action
    
    def get_children_totals(self):
        """Calculate totals from child lines"""
        totals = {
            'budget': 0.0,
            'actual': 0.0,
            'commitment': 0.0,
            'available': 0.0,
        }
        
        for child in self.child_ids:
            totals['budget'] += child.budget_amount
            totals['actual'] += child.actual_amount
            totals['commitment'] += child.commitment_amount
            totals['available'] += child.available_amount
        
        return totals
    
    def update_totals_from_children(self):
        """Update this line's totals from its children"""
        self.ensure_one()
        
        if self.child_ids:
            totals = self.get_children_totals()
            self.write({
                'budget_amount': totals['budget'],
                'actual_amount': totals['actual'],
                'commitment_amount': totals['commitment'],
                'available_amount': totals['available'],
            })