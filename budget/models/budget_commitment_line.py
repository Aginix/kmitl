import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class BudgetCommitmentLine(models.Model):
    """
    Budget Commitment Line - Individual budget allocation within a commitment.
    
    Business Purpose:
        Represents a single budget allocation within a multi-line commitment.
        Each line specifies exactly which budget account and analytic dimensions
        will be used, along with the amount to be committed.
    
    4D Analytic Distribution System:
        Each line implements the complete 4-dimensional analytic structure used
        throughout the KMITL budget system:
        
        1. Activities (กิจกรรม) - activity_analytic_id
           • แผนงาน/โครงการ/กิจกรรม hierarchy
           • Examples: งานบริหารทั่วไป > งานสำนักงาน > งานธุรการ
           
        2. Departments (ส่วนงาน) - department_analytic_id  
           • Organizational structure hierarchy
           • Examples: สำนักงานอธิการบดี > งานบุคคล > งานสรรหา
           • Inherited from parent commitment header
           
        3. Funds (กองทุน) - fund_analytic_id
           • Funding source hierarchy  
           • Examples: เงินรายได้ > เงินค่าบำรุง > เงินค่าสาธารณูปโภค
           
        4. Sources (แหล่งเงิน) - source_analytic_id
           • Money source classification
           • Examples: เงินแผ่นดิน, เงินนอกงบประมาณ, เงินบริจาค
           • Inherited from parent commitment header
    
    Real-time Budget Availability:
        Each line continuously calculates and displays:
        • Available budget amount (available_budget_amount)
        • Budget availability status (sufficient/warning/insufficient)
        • Percentage of available budget being requested
        • Color-coded visual feedback in the user interface
    
    Key Features:
        • Real-time budget availability checking with hierarchical matching
        • Automatic analytic validation and fund restrictions  
        • Consumption tracking through linked budget moves
        • Multi-currency support with proper currency handling
        • OnChange validations with user-friendly warnings
        • Integration with budget.controller for optimized calculations
    
    Data Relationships:
        • Parent: budget.commitment (header with department/source analytics)
        • References: budget.account (specific account being used)
        • Analytics: account.analytic.account (4D analytic dimensions)
        • Consumption: budget.move.line (via analytic matching)
    
    Calculation Logic:
        • Available Budget = Appropriated - Reserved - Consumed
        • Uses hierarchical matching for appropriation coverage
        • Excludes parent commitment from reserved calculation  
        • Real-time updates when analytic dimensions change
    
    Thai Localization:
        • Supports Thai government chart of accounts structure
        • Multi-level analytic hierarchies for Thai institutions
        • Currency handling for Thai Baht and foreign currencies
        • Validation rules aligned with Thai accounting practices
    
    Performance Features:
        • Computed fields with smart dependencies
        • Efficient parent_path hierarchy traversal
        • Optimized budget controller service integration
        • Minimal database queries through strategic caching
    """
    _name = "budget.commitment.line"
    _description = "Budget Commitment Line"
    _inherit = ["analytic.distribution.mixin", "mail.thread"]
    _order = "commitment_id, sequence, id"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Budget Commitment",
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Sequence for ordering lines",
    )

    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="Budget Account",
        required=True,
        index=True,
        tracking=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
    )

    name = fields.Char(
        string="Description",
        required=True,
        tracking=True,
    )

    amount = fields.Monetary(
        string="Committed Amount",
        required=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount to be committed for this budget line",
    )

    # 4-Dimensional Analytic Distribution
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "activities")],
        help="Activity dimension - แผนงาน/กิจกรรม",
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_department_analytic",
        store=True,
        readonly=True,
        help="Department from commitment header",
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "funds")],
        help="Fund dimension - กองทุน",
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_source_analytic",
        store=True,
        readonly=True,
        help="Source from commitment header",
    )

    # Related fields from parent
    date = fields.Date(
        related="commitment_id.date",
        store=True,
        string="Commitment Date",
    )

    date_range_fy_id = fields.Many2one(
        related="commitment_id.date_range_fy_id",
        store=True,
        string="Fiscal Year",
    )

    parent_state = fields.Selection(
        related="commitment_id.state",
        store=True,
        string="Commitment Status",
    )

    company_id = fields.Many2one(
        related="commitment_id.company_id",
        store=True,
        string="Company",
    )

    currency_id = fields.Many2one(
        related="commitment_id.currency_id",
        store=True,
        string="Currency",
    )

    # Budget account related fields
    budget_account_code = fields.Char(
        related="account_id.code",
        store=True,
        string="Budget Code",
    )

    budget_account_name = fields.Char(
        related="account_id.name",
        store=True,
        string="Budget Account Name",
    )

    budget_type = fields.Selection(
        related="account_id.budget_type",
        store=True,
        string="Budget Type",
    )

    # Consumption tracking
    consumed_amount = fields.Monetary(
        string="Consumed Amount",
        compute="_compute_consumed_amount",
        store=True,
        currency_field="currency_id",
        help="Amount already consumed from budget moves",
    )

    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_remaining_amount",
        store=True,
        currency_field="currency_id",
        help="Amount still available for consumption",
    )

    notes = fields.Text(
        string="Notes",
        help="Additional notes for this commitment line",
    )

    # Budget availability fields
    available_budget_amount = fields.Monetary(
        string="Available Budget",
        compute="_compute_available_budget",
        currency_field="currency_id",
        help="Available budget amount for this analytic combination",
    )
    
    budget_availability_status = fields.Selection(
        selection=[
            ('sufficient', 'Sufficient'),
            ('warning', 'Warning'),
            ('insufficient', 'Insufficient'),
        ],
        string="Budget Status",
        compute="_compute_available_budget",
        help="Budget availability status for this commitment",
    )
    
    budget_availability_percentage = fields.Float(
        string="% of Available",
        compute="_compute_available_budget",
        help="Percentage of available budget this commitment represents",
    )

    @api.depends("commitment_id.department_analytic_id")
    def _compute_department_analytic(self):
        """Department comes from the commitment header"""
        for line in self:
            line.department_analytic_id = line.commitment_id.department_analytic_id

    @api.depends("commitment_id.source_analytic_id")
    def _compute_source_analytic(self):
        """Source comes from the commitment header"""
        for line in self:
            line.source_analytic_id = line.commitment_id.source_analytic_id

    @api.depends("amount", "commitment_id.budget_move_ids.line_ids")
    def _compute_consumed_amount(self):
        """Calculate how much of this line has been consumed by budget moves"""
        for line in self:
            consumed = 0.0

            # Find budget move lines that match this commitment line's analytics
            related_moves = line.commitment_id.budget_move_ids.filtered(
                lambda m: m.state == "posted"
            )

            for move in related_moves:
                for move_line in move.line_ids:
                    # Check if budget move line matches this commitment line
                    if (move_line.account_id == line.account_id and
                        move_line.activity_analytic_id == line.activity_analytic_id and
                        move_line.fund_analytic_id == line.fund_analytic_id):
                        consumed += abs(move_line.balance)

            line.consumed_amount = min(consumed, line.amount)

    @api.depends("amount", "consumed_amount")
    def _compute_remaining_amount(self):
        """Calculate remaining amount available"""
        for line in self:
            line.remaining_amount = line.amount - line.consumed_amount

    @api.depends(
        "account_id", 
        "activity_analytic_id", 
        "fund_analytic_id",
        "department_analytic_id",
        "source_analytic_id",
        "amount",
        "commitment_id.date_range_fy_id",
        "commitment_id.state",
    )
    def _compute_available_budget(self):
        """
        Calculate real-time budget availability for this commitment line.
        
        This method provides the core functionality for real-time budget visibility,
        allowing users to see budget availability immediately as they create 
        commitment lines, rather than waiting until reservation time.
        
        Calculation Algorithm:
            1. Validate required fields (account, activity, fund, fiscal year)
            2. Prepare 4D analytic data structure for budget controller
            3. Call budget.controller.get_available_budget() for hierarchical calculation
            4. Adjust for self-reservation (if commitment already reserved)
            5. Calculate status and percentage indicators
        
        Budget Status Logic:
            • sufficient: Available >= Requested amount
            • warning: Available >= 50% of Requested amount  
            • insufficient: Available < 50% of Requested amount
            
        Real-time Triggers:
            This method is automatically called when:
            • Account selection changes (@api.onchange)
            • Activity analytic changes (@api.onchange) 
            • Fund analytic changes (@api.onchange)
            • Amount changes (@api.onchange)
            • Commitment state changes (via compute dependencies)
        
        Performance Optimizations:
            • Early validation skip for incomplete data
            • Leverages budget.controller optimized calculations
            • Smart dependency tracking prevents unnecessary recalculations
            • Graceful error handling with fallback values
        
        User Experience Features:
            • Color-coded visual feedback in tree view
            • Detailed warning messages for insufficient budget
            • Percentage indicators for budget utilization
            • Sum totals for multi-line commitments
        
        Error Handling:
            Gracefully handles calculation errors and provides fallback values:
            • available_budget_amount = 0.0
            • budget_availability_status = 'insufficient'  
            • budget_availability_percentage = 0.0
            
        Integration Points:
            • budget.controller: Centralized calculation service
            • Budget tree view: Real-time visual feedback
            • OnChange warnings: User guidance for insufficient budget
            • Budget execution reports: Consistent calculation methodology
        """
        budget_controller = self.env['budget.controller']
        
        for line in self:
            if not all([
                line.account_id,
                line.activity_analytic_id,
                line.fund_analytic_id,
                line.commitment_id.date_range_fy_id
            ]):
                line.available_budget_amount = 0.0
                line.budget_availability_status = 'insufficient'
                line.budget_availability_percentage = 0.0
                continue
            
            # Prepare analytic data for budget controller
            analytic_data = {
                'account_id': line.account_id.id,
                'activity_analytic_id': line.activity_analytic_id.id,
                'department_analytic_id': line.department_analytic_id.id if line.department_analytic_id else False,
                'fund_analytic_id': line.fund_analytic_id.id,
                'source_analytic_id': line.source_analytic_id.id if line.source_analytic_id else False,
            }
            
            try:
                # Get available budget amount
                available = budget_controller.get_available_budget(
                    analytic_data,
                    line.commitment_id.date_range_fy_id.id,
                    line.company_id.id
                )
                
                # If commitment is already reserved, add back its own amount to available
                if line.commitment_id.state == 'reserved' and line.amount:
                    available += line.amount
                
                line.available_budget_amount = available
                
                # Calculate status and percentage
                if line.amount:
                    if available >= line.amount:
                        line.budget_availability_status = 'sufficient'
                    elif available >= line.amount * 0.5:  # 50% threshold
                        line.budget_availability_status = 'warning'
                    else:
                        line.budget_availability_status = 'insufficient'
                    
                    line.budget_availability_percentage = (line.amount / available * 100) if available > 0 else 999.99
                else:
                    line.budget_availability_status = 'sufficient'
                    line.budget_availability_percentage = 0.0
                    
            except Exception as e:
                _logger.warning("Error calculating budget availability for line %s: %s", line.id, str(e))
                line.available_budget_amount = 0.0
                line.budget_availability_status = 'insufficient'
                line.budget_availability_percentage = 0.0

    @api.onchange("account_id")
    def _onchange_account_id(self):
        """Update name when budget account changes"""
        if self.account_id:
            if not self.name:
                self.name = self.account_id.name

    @api.onchange("fund_analytic_id", "account_id")
    def _onchange_fund_account_validation(self):
        """Validate that budget account is allowed for selected fund"""
        if self.fund_analytic_id and self.account_id:
            # Check if budget account has fund restrictions
            if self.account_id.fund_analytic_ids:
                if self.fund_analytic_id not in self.account_id.fund_analytic_ids:
                    return {
                        'warning': {
                            'title': _('Fund Restriction'),
                            'message': _('Budget account %s is not allowed for fund %s') % (
                                self.account_id.name,
                                self.fund_analytic_id.name
                            )
                        }
                    }

    @api.onchange("amount", "account_id", "activity_analytic_id", "fund_analytic_id")
    def _onchange_check_budget_availability(self):
        """Check budget availability and show warning if insufficient"""
        if self.amount and self.available_budget_amount >= 0:
            if self.budget_availability_status == 'insufficient':
                return {
                    'warning': {
                        'title': _('Insufficient Budget'),
                        'message': _(
                            'The requested amount (%(requested)s) exceeds the available budget (%(available)s).\n\n'
                            'Budget Account: %(account)s\n'
                            'Activity: %(activity)s\n'
                            'Fund: %(fund)s\n\n'
                            'Please reduce the amount or select a different analytic combination.'
                        ) % {
                            'requested': "{:,.2f}".format(self.amount),
                            'available': "{:,.2f}".format(self.available_budget_amount),
                            'account': self.account_id.display_name if self.account_id else 'N/A',
                            'activity': self.activity_analytic_id.display_name if self.activity_analytic_id else 'N/A',
                            'fund': self.fund_analytic_id.display_name if self.fund_analytic_id else 'N/A',
                        }
                    }
                }
            elif self.budget_availability_status == 'warning':
                return {
                    'warning': {
                        'title': _('Low Budget Warning'),
                        'message': _(
                            'This commitment will use %(percentage).1f%% of the available budget.\n\n'
                            'Requested: %(requested)s\n'
                            'Available: %(available)s\n'
                            'Remaining after commitment: %(remaining)s'
                        ) % {
                            'percentage': self.budget_availability_percentage,
                            'requested': "{:,.2f}".format(self.amount),
                            'available': "{:,.2f}".format(self.available_budget_amount),
                            'remaining': "{:,.2f}".format(self.available_budget_amount - self.amount),
                        }
                    }
                }

    @api.constrains("amount")
    def _check_positive_amount(self):
        """Ensure commitment amount is positive"""
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_("Commitment amount must be positive."))

    @api.constrains("activity_analytic_id", "fund_analytic_id", "account_id")
    def _check_required_analytics(self):
        """Ensure all required analytic dimensions are set"""
        for line in self:
            if not line.activity_analytic_id:
                raise ValidationError(_("Activity analytic account is required."))
            if not line.fund_analytic_id:
                raise ValidationError(_("Fund analytic account is required."))
            if not line.account_id:
                raise ValidationError(_("Budget account is required."))

    def name_get(self):
        """Custom name display"""
        result = []
        for line in self:
            name = f"[{line.budget_account_code}] {line.name}"
            if line.amount:
                name += f" - {line.currency_id.symbol}{line.amount:,.2f}"
            result.append((line.id, name))
        return result

    @api.model
    def get_analytic_distribution(self):
        """Build analytic distribution dictionary for integration"""
        distribution = {}

        if self.activity_analytic_id:
            distribution[str(self.activity_analytic_id.id)] = 100.0
        if self.department_analytic_id:
            distribution[str(self.department_analytic_id.id)] = 100.0
        if self.fund_analytic_id:
            distribution[str(self.fund_analytic_id.id)] = 100.0
        if self.source_analytic_id:
            distribution[str(self.source_analytic_id.id)] = 100.0

        return distribution

    @api.model
    def get_suggested_budget_accounts(self, activity_id, fund_id, department_id=False, source_id=False, limit=5):
        """
        Get suggested budget accounts with available funds for the given analytic combination
        
        Returns list of tuples: [(account_id, account_name, available_amount), ...]
        """
        if not all([activity_id, fund_id]):
            return []
        
        budget_controller = self.env['budget.controller']
        suggestions = []
        
        # Get all expense budget accounts
        budget_accounts = self.env['budget.account'].search([
            ('budgetable', '=', True),
            ('budget_type', '=', 'expense'),
        ])
        
        # Get fiscal year
        today = fields.Date.today()
        fiscal_year = self.env['account.fiscal.year'].search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        
        if not fiscal_year:
            return []
        
        # Check availability for each account
        for account in budget_accounts[:20]:  # Limit to first 20 to avoid performance issues
            analytic_data = {
                'account_id': account.id,
                'activity_analytic_id': activity_id,
                'department_analytic_id': department_id or False,
                'fund_analytic_id': fund_id,
                'source_analytic_id': source_id or False,
            }
            
            try:
                available = budget_controller.get_available_budget(
                    analytic_data,
                    fiscal_year.id,
                    self.env.company.id
                )
                
                if available > 0:
                    suggestions.append((
                        account.id,
                        f"[{account.code}] {account.name}",
                        available
                    ))
            except:
                continue
        
        # Sort by available amount descending and return top results
        suggestions.sort(key=lambda x: x[2], reverse=True)
        return suggestions[:limit]
    
    def create_budget_move_line(self, move_id, amount):
        """Helper method to create budget move line from commitment line"""
        self.ensure_one()

        budget_move_line_vals = {
            'move_id': move_id,
            'account_id': self.account_id.id,
            'name': self.name,
            'balance': amount,
            'activity_analytic_id': self.activity_analytic_id.id,
            'department_analytic_id': self.department_analytic_id.id,
            'fund_analytic_id': self.fund_analytic_id.id,
            'source_analytic_id': self.source_analytic_id.id,
            'notes': f"From commitment: {self.commitment_id.name}",
        }

        return self.env['budget.move.line'].create(budget_move_line_vals)
