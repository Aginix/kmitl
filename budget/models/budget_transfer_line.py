from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BudgetTransferLine(models.Model):
    """
    Budget Transfer Line - Individual transfer line items.
    
    Each line represents either a source (from) or destination (to) 
    for the budget transfer with specific budget account and analytics.
    """
    
    _name = "budget.transfer.line"
    _description = "Budget Transfer Line"
    _order = "transfer_id, sequence, id"
    
    # Basic Fields
    transfer_id = fields.Many2one(
        comodel_name="budget.transfer",
        string="Budget Transfer",
        required=True,
        ondelete="cascade",
    )
    
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Sequence for ordering transfer lines"
    )
    
    transfer_direction = fields.Selection(
        selection=[
            ("from", "Transfer From (Source)"),
            ("to", "Transfer To (Destination)"),
        ],
        string="Direction",
        required=True,
        help="Direction of this transfer line"
    )
    
    # Budget Account
    budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="Budget Account",
        required=True,
        help="Budget account for this transfer line"
    )
    
    # Amount
    amount = fields.Float(
        string="Amount",
        required=True,
        digits="Budget Precision",
        help="Transfer amount for this line"
    )
    
    # Analytics Distribution
    analytic_distribution = fields.Json(
        string="Analytic Distribution",
        help="JSON containing the analytic distribution for this line"
    )
    
    # Analytic Display Fields (for easier UI handling)
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_fields",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        help="Activity analytic account"
    )
    
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน", 
        compute="_compute_analytic_fields",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        help="Department analytic account"
    )
    
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_fields", 
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        help="Fund analytic account"
    )
    
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_fields",
        inverse="_inverse_source_analytic", 
        domain=[("root_plan_id.code", "=", "sources")],
        help="Source analytic account"
    )
    
    # Description
    description = fields.Char(
        string="Description",
        help="Description for this transfer line"
    )
    
    # Company and Currency (inherited from transfer)
    company_id = fields.Many2one(
        related="transfer_id.company_id",
        store=True,
        readonly=True
    )
    
    currency_id = fields.Many2one(
        related="transfer_id.currency_id", 
        store=True,
        readonly=True
    )
    
    # Budget Availability Check
    available_budget = fields.Float(
        string="Available Budget",
        compute="_compute_available_budget",
        help="Available budget for this account and analytics"
    )
    
    budget_sufficient = fields.Boolean(
        string="Budget Sufficient",
        compute="_compute_available_budget",
        help="True if available budget is sufficient for this transfer"
    )
    
    @api.depends("analytic_distribution")
    def _compute_analytic_fields(self):
        """Compute individual analytic fields from JSON distribution"""
        for line in self:
            if not line.analytic_distribution:
                line.activity_analytic_id = False
                line.department_analytic_id = False
                line.fund_analytic_id = False
                line.source_analytic_id = False
                continue
            
            # Extract analytic account IDs from distribution
            # Distribution format: {analytic_account_id: percentage}
            distribution = line.analytic_distribution or {}
            
            # Get all analytic accounts in distribution
            analytic_ids = [int(aid) for aid in distribution.keys() if aid.isdigit()]
            analytics = self.env["account.analytic.account"].browse(analytic_ids)
            
            # Map to appropriate fields based on plan code
            line.activity_analytic_id = analytics.filtered(
                lambda a: a.root_plan_id.code == "activities"
            )[:1]
            line.department_analytic_id = analytics.filtered(
                lambda a: a.root_plan_id.code == "departments" 
            )[:1]
            line.fund_analytic_id = analytics.filtered(
                lambda a: a.root_plan_id.code == "funds"
            )[:1]
            line.source_analytic_id = analytics.filtered(
                lambda a: a.root_plan_id.code == "sources"
            )[:1]
    
    def _update_analytic_distribution(self):
        """Update analytic distribution JSON from individual fields"""
        self.ensure_one()
        
        distribution = {}
        analytic_accounts = [
            self.activity_analytic_id,
            self.department_analytic_id, 
            self.fund_analytic_id,
            self.source_analytic_id
        ]
        
        # Add each analytic account with 100% distribution
        for account in analytic_accounts:
            if account:
                distribution[str(account.id)] = 100.0
        
        self.analytic_distribution = distribution if distribution else False
    
    def _inverse_activity_analytic(self):
        """Update distribution when activity changes"""
        for line in self:
            line._update_analytic_distribution()
    
    def _inverse_department_analytic(self):
        """Update distribution when department changes"""
        for line in self:
            line._update_analytic_distribution()
    
    def _inverse_fund_analytic(self):
        """Update distribution when fund changes"""  
        for line in self:
            line._update_analytic_distribution()
    
    def _inverse_source_analytic(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution()
    
    @api.depends(
        "budget_account_id", 
        "analytic_distribution", 
        "amount",
        "transfer_direction",
        "transfer_id.date_range_fy_id"
    )
    def _compute_available_budget(self):
        """Compute available budget for source lines"""
        for line in self:
            if line.transfer_direction != "from" or not line.budget_account_id:
                line.available_budget = 0.0
                line.budget_sufficient = True
                continue
            
            try:
                # Use budget controller to get available budget
                budget_controller = self.env["budget.controller"]
                fiscal_year_id = line.transfer_id.date_range_fy_id.id if line.transfer_id.date_range_fy_id else False
                
                available = budget_controller.get_available_budget(
                    budget_account_id=line.budget_account_id.id,
                    analytic_distribution=line.analytic_distribution or {},
                    fiscal_year_id=fiscal_year_id
                )
                
                line.available_budget = available
                line.budget_sufficient = available >= line.amount
                
            except Exception:
                # If budget controller fails, assume no budget available
                line.available_budget = 0.0
                line.budget_sufficient = False
    
    @api.constrains("amount")
    def _check_amount_positive(self):
        """Ensure amount is positive"""
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_("Transfer amount must be greater than zero"))
    
    @api.constrains("transfer_direction", "budget_account_id", "analytic_distribution")
    def _check_duplicate_lines(self):
        """Prevent duplicate transfer lines with same direction, account and analytics"""
        for line in self:
            if not line.budget_account_id:
                continue
                
            domain = [
                ("transfer_id", "=", line.transfer_id.id),
                ("transfer_direction", "=", line.transfer_direction),
                ("budget_account_id", "=", line.budget_account_id.id),
                ("analytic_distribution", "=", line.analytic_distribution),
                ("id", "!=", line.id),
            ]
            
            duplicate = self.search(domain, limit=1)
            if duplicate:
                raise ValidationError(_(
                    "Duplicate transfer line found. Each combination of direction, "
                    "budget account and analytic distribution must be unique."
                ))
    
    @api.onchange("budget_account_id", "analytic_distribution", "amount")
    def _onchange_budget_validation(self):
        """Show warning if insufficient budget"""
        if (self.transfer_direction == "from" and 
            self.budget_account_id and 
            self.amount > 0):
            
            # Trigger computation of available budget
            self._compute_available_budget()
            
            if not self.budget_sufficient:
                return {
                    "warning": {
                        "title": _("Insufficient Budget"),
                        "message": _(
                            "Available budget ({:,.2f}) is less than transfer amount ({:,.2f}). "
                            "This transfer may fail validation."
                        ).format(self.available_budget, self.amount)
                    }
                }
    
    @api.model
    def create_transfer_pair(self, from_vals, to_vals):
        """
        Helper method to create balanced from/to transfer line pairs
        
        Args:
            from_vals: Values for the 'from' line
            to_vals: Values for the 'to' line
        
        Returns:
            Tuple of (from_line, to_line) records
        """
        # Ensure amounts match
        if from_vals.get("amount") != to_vals.get("amount"):
            raise ValidationError(_("From and To amounts must match"))
        
        # Set directions
        from_vals["transfer_direction"] = "from"
        to_vals["transfer_direction"] = "to"
        
        # Create lines
        from_line = self.create(from_vals)
        to_line = self.create(to_vals)
        
        return from_line, to_line
    
    def name_get(self):
        """Custom name display for transfer lines"""
        result = []
        for line in self:
            direction = "FROM" if line.transfer_direction == "from" else "TO"
            account_name = line.budget_account_id.display_name if line.budget_account_id else "No Account"
            amount = "{:,.2f}".format(line.amount) if line.amount else "0.00"
            
            name = f"{direction} {account_name} - {amount}"
            result.append((line.id, name))
        
        return result