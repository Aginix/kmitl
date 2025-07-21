from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class BudgetTransferWizard(models.TransientModel):
    """
    User-friendly wizard for creating budget transfers.
    
    This wizard provides a step-by-step interface that hides the complexity
    of double-entry bookkeeping from users and focuses on UX.
    
    Steps:
    1. Basic transfer information (amount, reason, type)
    2. Source selection (where to transfer FROM)
    3. Destination selection (where to transfer TO)
    4. Review and create transfer
    """
    
    _name = "budget.transfer.wizard"
    _description = "Budget Transfer Creation Wizard"
    
    # Step tracking
    current_step = fields.Integer(
        string="Current Step",
        default=1,
        help="Current step in the wizard (1-4)"
    )
    
    # Basic Information (Step 1)
    amount = fields.Float(
        string="Transfer Amount",
        required=True,
        digits="Budget Precision",
        help="Amount to transfer"
    )
    
    transfer_reason = fields.Text(
        string="Transfer Reason",
        required=True,
        help="Please explain why this budget transfer is needed"
    )
    
    transfer_type = fields.Selection(
        selection=[
            ("between_accounts", "Between Budget Accounts"),
            ("between_departments", "Between Departments"),
            ("between_sources", "Between Funding Sources"),
        ],
        string="Transfer Type",
        required=True,
        default="between_accounts",
        help="Type of budget transfer"
    )
    
    transfer_date = fields.Date(
        string="Transfer Date",
        required=True,
        default=lambda self: fields.Date.context_today(self),
        help="Date of the transfer"
    )
    
    # Source Information (Step 2)
    from_budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="Transfer FROM Account",
        help="Budget account to transfer FROM"
    )
    
    from_activity_id = fields.Many2one(
        "account.analytic.account",
        string="FROM กิจกรรม",
        domain=[("root_plan_id.code", "=", "activities")],
        help="Activity to transfer from"
    )
    
    from_department_id = fields.Many2one(
        "account.analytic.account",
        string="FROM ส่วนงาน",
        domain=[("root_plan_id.code", "=", "departments")],
        help="Department to transfer from"
    )
    
    from_fund_id = fields.Many2one(
        "account.analytic.account",
        string="FROM กองทุน",
        domain=[("root_plan_id.code", "=", "funds")],
        help="Fund to transfer from"
    )
    
    from_source_id = fields.Many2one(
        "account.analytic.account",
        string="FROM แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
        help="Source to transfer from"
    )
    
    # Available budget for source
    available_budget_from = fields.Float(
        string="Available Budget (FROM)",
        compute="_compute_available_budget",
        help="Available budget in source account"
    )
    
    budget_sufficient_from = fields.Boolean(
        string="Sufficient Budget",
        compute="_compute_available_budget",
        help="Whether source has sufficient budget"
    )
    
    # Destination Information (Step 3)
    to_budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="Transfer TO Account",
        help="Budget account to transfer TO"
    )
    
    to_activity_id = fields.Many2one(
        "account.analytic.account",
        string="TO กิจกรรม",
        domain=[("root_plan_id.code", "=", "activities")],
        help="Activity to transfer to"
    )
    
    to_department_id = fields.Many2one(
        "account.analytic.account",
        string="TO ส่วนงาน", 
        domain=[("root_plan_id.code", "=", "departments")],
        help="Department to transfer to"
    )
    
    to_fund_id = fields.Many2one(
        "account.analytic.account",
        string="TO กองทุน",
        domain=[("root_plan_id.code", "=", "funds")],
        help="Fund to transfer to"
    )
    
    to_source_id = fields.Many2one(
        "account.analytic.account",
        string="TO แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
        help="Source to transfer to"
    )
    
    # Company and fiscal year
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    
    fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        compute="_compute_fiscal_year",
        help="Fiscal year for this transfer"
    )
    
    # Step visibility flags
    show_step_1 = fields.Boolean(compute="_compute_step_visibility", default=True)
    show_step_2 = fields.Boolean(compute="_compute_step_visibility")
    show_step_3 = fields.Boolean(compute="_compute_step_visibility")
    show_step_4 = fields.Boolean(compute="_compute_step_visibility")
    
    # Navigation buttons visibility
    show_next_button = fields.Boolean(compute="_compute_button_visibility")
    show_previous_button = fields.Boolean(compute="_compute_button_visibility")
    show_create_button = fields.Boolean(compute="_compute_button_visibility")
    
    # Validation messages
    validation_message = fields.Html(
        string="Validation Message",
        compute="_compute_validation_message"
    )
    
    @api.depends("current_step")
    def _compute_step_visibility(self):
        """Control which step is visible"""
        for wizard in self:
            current_step = wizard.current_step or 1  # Default to step 1 if not set
            wizard.show_step_1 = (current_step == 1)
            wizard.show_step_2 = (current_step == 2)
            wizard.show_step_3 = (current_step == 3)
            wizard.show_step_4 = (current_step == 4)
    
    @api.depends("current_step")
    def _compute_button_visibility(self):
        """Control button visibility"""
        for wizard in self:
            current_step = wizard.current_step or 1  # Default to step 1 if not set
            wizard.show_next_button = current_step < 4
            wizard.show_previous_button = current_step > 1
            wizard.show_create_button = current_step == 4
    
    @api.depends("transfer_date", "company_id")
    def _compute_fiscal_year(self):
        """Compute fiscal year from transfer date"""
        for wizard in self:
            if wizard.transfer_date and wizard.company_id:
                fiscal_year = self.env["account.fiscal.year"].search([
                    ("date_from", "<=", wizard.transfer_date),
                    ("date_to", ">=", wizard.transfer_date),
                    ("company_id", "=", wizard.company_id.id)
                ], limit=1)
                wizard.fiscal_year_id = fiscal_year
            else:
                wizard.fiscal_year_id = False
    
    @api.depends(
        "from_budget_account_id", "from_activity_id", "from_department_id",
        "from_fund_id", "from_source_id", "amount", "fiscal_year_id"
    )
    def _compute_available_budget(self):
        """Compute available budget for source"""
        for wizard in self:
            if not wizard.from_budget_account_id or not wizard.amount:
                wizard.available_budget_from = 0.0
                wizard.budget_sufficient_from = False
                continue
            
            try:
                # Build analytic distribution
                distribution = {}
                analytics = [
                    wizard.from_activity_id,
                    wizard.from_department_id,
                    wizard.from_fund_id,
                    wizard.from_source_id
                ]
                
                for analytic in analytics:
                    if analytic:
                        distribution[str(analytic.id)] = 100.0
                
                # Get available budget
                budget_controller = self.env["budget.controller"]
                available = budget_controller.get_available_budget(
                    budget_account_id=wizard.from_budget_account_id.id,
                    analytic_distribution=distribution,
                    fiscal_year_id=wizard.fiscal_year_id.id if wizard.fiscal_year_id else False
                )
                
                wizard.available_budget_from = available
                wizard.budget_sufficient_from = available >= wizard.amount
                
            except Exception:
                wizard.available_budget_from = 0.0
                wizard.budget_sufficient_from = False
    
    @api.depends(
        "current_step", "amount", "transfer_reason", "from_budget_account_id",
        "to_budget_account_id", "budget_sufficient_from"
    )
    def _compute_validation_message(self):
        """Generate validation messages for current step"""
        for wizard in self:
            messages = []
            current_step = wizard.current_step or 1  # Default to step 1 if not set
            
            if current_step == 1:
                # Basic info validation
                if not wizard.amount or wizard.amount <= 0:
                    messages.append("⚠️ Please enter a transfer amount greater than zero")
                if not wizard.transfer_reason:
                    messages.append("⚠️ Please provide a reason for this transfer")
                
            elif current_step == 2:
                # Source validation
                if not wizard.from_budget_account_id:
                    messages.append("⚠️ Please select source budget account")
                elif not wizard.budget_sufficient_from:
                    shortage = wizard.amount - wizard.available_budget_from
                    messages.append(
                        f"❌ <strong>Insufficient Budget</strong><br/>"
                        f"Available: {wizard.available_budget_from:,.2f}<br/>"
                        f"Required: {wizard.amount:,.2f}<br/>"
                        f"Shortage: {shortage:,.2f}"
                    )
                else:
                    messages.append(
                        f"✅ <strong>Budget Available</strong><br/>"
                        f"Available: {wizard.available_budget_from:,.2f}<br/>"
                        f"Transfer: {wizard.amount:,.2f}<br/>"
                        f"Remaining: {wizard.available_budget_from - wizard.amount:,.2f}"
                    )
                
            elif current_step == 3:
                # Destination validation
                if not wizard.to_budget_account_id:
                    messages.append("⚠️ Please select destination budget account")
                
                # Check for same source and destination
                if (wizard.from_budget_account_id == wizard.to_budget_account_id and
                    wizard.from_activity_id == wizard.to_activity_id and
                    wizard.from_department_id == wizard.to_department_id and
                    wizard.from_fund_id == wizard.to_fund_id and
                    wizard.from_source_id == wizard.to_source_id):
                    messages.append("❌ Source and destination cannot be the same")
                
            elif current_step == 4:
                # Final review
                if wizard.budget_sufficient_from:
                    messages.append("✅ Ready to create budget transfer")
                else:
                    messages.append("❌ Cannot create transfer - insufficient budget")
            
            wizard.validation_message = "<br/>".join(messages) if messages else ""
    
    def action_next_step(self):
        """Move to next step with validation"""
        self.ensure_one()
        
        # Validate current step
        if self.current_step == 1:
            if not self.amount or self.amount <= 0:
                raise ValidationError(_("Please enter a valid transfer amount"))
            if not self.transfer_reason:
                raise ValidationError(_("Please provide a reason for this transfer"))
        
        elif self.current_step == 2:
            if not self.from_budget_account_id:
                raise ValidationError(_("Please select source budget account"))
            if not self.budget_sufficient_from:
                raise ValidationError(_(
                    "Insufficient budget. Available: {}, Required: {}"
                ).format(self.available_budget_from, self.amount))
        
        elif self.current_step == 3:
            if not self.to_budget_account_id:
                raise ValidationError(_("Please select destination budget account"))
        
        # Move to next step
        self.current_step += 1
        
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.transfer.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }
    
    def action_previous_step(self):
        """Move to previous step"""
        self.ensure_one()
        self.current_step -= 1
        
        return {
            "type": "ir.actions.act_window", 
            "res_model": "budget.transfer.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }
    
    def action_create_transfer(self):
        """Create the budget transfer"""
        self.ensure_one()
        
        # Final validation
        self._validate_transfer_complete()
        
        # Create transfer
        transfer_vals = {
            "amount": self.amount,
            "reason": self.transfer_reason,
            "transfer_type": self.transfer_type,
            "date": self.transfer_date,
            "company_id": self.company_id.id,
            "date_range_fy_id": self.fiscal_year_id.id,
            "user_id": self.env.user.id,
        }
        
        transfer = self.env["budget.transfer"].create(transfer_vals)
        
        # Create transfer lines
        self._create_transfer_lines(transfer)
        
        # Return action to view the created transfer
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.transfer",
            "view_mode": "form",
            "res_id": transfer.id,
            "target": "current",
            "name": _("Budget Transfer Created"),
        }
    
    def _validate_transfer_complete(self):
        """Validate complete transfer before creation"""
        errors = []
        
        if not self.amount or self.amount <= 0:
            errors.append(_("Invalid transfer amount"))
        
        if not self.from_budget_account_id:
            errors.append(_("Source budget account not selected"))
        
        if not self.to_budget_account_id:
            errors.append(_("Destination budget account not selected"))
        
        if not self.budget_sufficient_from:
            errors.append(_("Insufficient budget in source account"))
        
        # Check if same source and destination
        if (self.from_budget_account_id == self.to_budget_account_id and
            self.from_activity_id == self.to_activity_id and
            self.from_department_id == self.to_department_id and
            self.from_fund_id == self.to_fund_id and
            self.from_source_id == self.to_source_id):
            errors.append(_("Source and destination cannot be the same"))
        
        if errors:
            raise ValidationError("\n".join(errors))
    
    def _create_transfer_lines(self, transfer):
        """Create transfer lines for the transfer"""
        self.ensure_one()
        
        # Build analytic distributions
        from_distribution = {}
        to_distribution = {}
        
        # From analytics
        from_analytics = [
            self.from_activity_id,
            self.from_department_id,
            self.from_fund_id,
            self.from_source_id
        ]
        
        for analytic in from_analytics:
            if analytic:
                from_distribution[str(analytic.id)] = 100.0
        
        # To analytics
        to_analytics = [
            self.to_activity_id,
            self.to_department_id,
            self.to_fund_id,
            self.to_source_id
        ]
        
        for analytic in to_analytics:
            if analytic:
                to_distribution[str(analytic.id)] = 100.0
        
        # Create FROM line
        from_line_vals = {
            "transfer_id": transfer.id,
            "transfer_direction": "from",
            "budget_account_id": self.from_budget_account_id.id,
            "amount": self.amount,
            "analytic_distribution": from_distribution,
            "description": f"Transfer from {self.from_budget_account_id.name}",
            "sequence": 10,
        }
        
        # Create TO line
        to_line_vals = {
            "transfer_id": transfer.id,
            "transfer_direction": "to",
            "budget_account_id": self.to_budget_account_id.id,
            "amount": self.amount,
            "analytic_distribution": to_distribution,
            "description": f"Transfer to {self.to_budget_account_id.name}",
            "sequence": 20,
        }
        
        self.env["budget.transfer.line"].create([from_line_vals, to_line_vals])
    
    @api.onchange("from_budget_account_id", "from_activity_id", "from_department_id", "from_fund_id", "from_source_id")
    def _onchange_source_fields(self):
        """Show budget availability when source changes"""
        if self.current_step == 2 and self.from_budget_account_id and self.amount:
            # Trigger budget computation
            self._compute_available_budget()
    
    @api.onchange("transfer_type")
    def _onchange_transfer_type(self):
        """Clear analytics when transfer type changes"""
        # Reset analytics when type changes
        if self.transfer_type:
            # Keep the relevant analytics based on type
            if self.transfer_type != "between_departments":
                pass  # Keep current department selection
            if self.transfer_type != "between_sources":
                pass  # Keep current source selection