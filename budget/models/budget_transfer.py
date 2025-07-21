from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class BudgetTransfer(models.Model):
    """
    Budget Transfer - Handle budget transfers between accounts with approval workflow.
    
    Business Purpose:
        Budget transfers allow moving allocated budget amounts from one budget account
        to another within the same fiscal year, subject to approval workflow and
        availability validation.
    
    Features:
        • Multi-step approval workflow (draft → submitted → approved → posted)
        • Budget availability checking before transfer
        • User-friendly UI that hides double-entry complexity
        • Complete audit trail via mail.thread
        • Email notifications for approval process
        • Integration with existing budget.move system
    
    State Lifecycle:
        draft → submitted → approved → posted → rejected/cancelled
        │       │           │         │        │
        │       │           │         │        └── Transfer rejected or cancelled
        │       │           │         └─────────── Creates budget.move entries
        │       │           └───────────────────── Ready for posting
        │       └───────────────────────────────── Under review by approvers
        └───────────────────────────────────────── Editable by requestor
    """
    
    _name = "budget.transfer"
    _description = "Budget Transfer"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "ref"]
    
    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "approved": [("readonly", True)],
        "posted": [("readonly", True)],
        "rejected": [("readonly", True)],
        "cancelled": [("readonly", True)],
    }
    
    # Basic Information
    name = fields.Char(
        string="Transfer Number",
        compute="_compute_name",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
    )
    
    ref = fields.Char(
        string="Reference", 
        copy=False, 
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    
    date = fields.Date(
        string="Transfer Date",
        index=True,
        default=lambda self: fields.Date.context_today(self),
        required=True,
        readonly=False,
        copy=False,
        tracking=True,
        states=READONLY_STATES,
    )
    
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("posted", "Posted"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )
    
    # Transfer Details
    transfer_type = fields.Selection(
        selection=[
            ("between_accounts", "Between Budget Accounts"),
            ("between_departments", "Between Departments"),
            ("between_sources", "Between Funding Sources"),
        ],
        string="Transfer Type",
        required=True,
        default="between_accounts",
        readonly=False,
        states=READONLY_STATES,
        tracking=True,
    )
    
    amount = fields.Float(
        string="Transfer Amount",
        required=True,
        digits="Budget Precision",
        readonly=False,
        states=READONLY_STATES,
        tracking=True,
    )
    
    reason = fields.Text(
        string="Transfer Reason",
        required=True,
        readonly=False,
        states=READONLY_STATES,
        tracking=True,
        help="Please provide detailed justification for this budget transfer"
    )
    
    # Company and Currency
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        tracking=True,
        store=True,
        required=True,
    )
    
    # Fiscal Year
    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    
    # User Management
    user_id = fields.Many2one(
        string="Requested by",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        required=True,
        readonly=False,
        states=READONLY_STATES,
    )
    
    # Approval Fields
    approver_id = fields.Many2one(
        string="Approved by",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        readonly=True,
    )
    
    approval_date = fields.Datetime(
        string="Approval Date",
        copy=False,
        tracking=True,
        readonly=True,
    )
    
    rejection_reason = fields.Text(
        string="Rejection Reason",
        readonly=True,
        tracking=True,
    )
    
    # Transfer Lines
    line_ids = fields.One2many(
        comodel_name="budget.transfer.line",
        inverse_name="transfer_id",
        string="Transfer Lines",
        copy=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    
    # Generated Budget Moves
    budget_move_ids = fields.One2many(
        comodel_name="budget.move",
        inverse_name="transfer_id",
        string="Generated Budget Moves",
        readonly=True,
        help="Budget moves created when this transfer is posted"
    )
    
    # Button Visibility
    show_submit_button = fields.Boolean(
        compute="_compute_button_visibility"
    )
    show_approve_button = fields.Boolean(
        compute="_compute_button_visibility"
    )
    show_reject_button = fields.Boolean(
        compute="_compute_button_visibility"
    )
    show_post_button = fields.Boolean(
        compute="_compute_button_visibility"
    )
    show_cancel_button = fields.Boolean(
        compute="_compute_button_visibility"
    )
    show_reset_button = fields.Boolean(
        compute="_compute_button_visibility"
    )
    
    # Validation Fields
    has_sufficient_budget = fields.Boolean(
        compute="_compute_budget_validation",
        help="Indicates if source has sufficient budget for transfer"
    )
    
    budget_validation_message = fields.Text(
        compute="_compute_budget_validation",
        help="Detailed budget validation message"
    )
    
    @api.depends("state", "date")
    def _compute_name(self):
        """Generate transfer number based on date and sequence"""
        for transfer in self:
            if transfer.state == "cancelled":
                continue
                
            has_name = transfer.name and transfer.name != "New"
            if has_name or transfer.state == "draft":
                continue
                
            if not has_name and transfer.date:
                transfer.name = self.env["ir.sequence"].next_by_code("budget.transfer") or _("New")
    
    @api.depends("state", "user_id")
    def _compute_button_visibility(self):
        """Control button visibility based on state and user permissions"""
        for transfer in self:
            user = self.env.user
            
            # Submit button - only in draft state for requestor
            transfer.show_submit_button = (
                transfer.state == "draft" and 
                transfer.user_id == user
            )
            
            # Approve/Reject buttons - only for approvers in submitted state
            can_approve = user.has_group("budget.group_budget_transfer_approver")
            transfer.show_approve_button = (
                transfer.state == "submitted" and 
                can_approve
            )
            transfer.show_reject_button = (
                transfer.state == "submitted" and 
                can_approve
            )
            
            # Post button - only for managers in approved state
            can_manage = user.has_group("budget.group_budget_transfer_manager")
            transfer.show_post_button = (
                transfer.state == "approved" and 
                can_manage
            )
            
            # Cancel button - available in draft/submitted states
            transfer.show_cancel_button = (
                transfer.state in ("draft", "submitted") and
                (transfer.user_id == user or can_approve or can_manage)
            )
            
            # Reset button - available for managers in non-draft states
            transfer.show_reset_button = (
                transfer.state != "draft" and 
                can_manage
            )
    
    @api.depends("line_ids", "amount", "state")
    def _compute_budget_validation(self):
        """Validate budget availability for transfer"""
        for transfer in self:
            if not transfer.line_ids or transfer.state in ("posted", "cancelled"):
                transfer.has_sufficient_budget = True
                transfer.budget_validation_message = ""
                continue
            
            try:
                # Validate each line's budget availability
                validation_results = []
                
                for line in transfer.line_ids.filtered(lambda l: l.transfer_direction == "from"):
                    # Check budget availability using budget controller
                    budget_controller = self.env["budget.controller"]
                    available_budget = budget_controller.get_available_budget(
                        budget_account_id=line.budget_account_id.id,
                        analytic_distribution=line.analytic_distribution or {},
                        fiscal_year_id=transfer.date_range_fy_id.id
                    )
                    
                    if available_budget < line.amount:
                        shortage = line.amount - available_budget
                        validation_results.append({
                            "line": line,
                            "available": available_budget,
                            "required": line.amount,
                            "shortage": shortage,
                            "valid": False
                        })
                    else:
                        validation_results.append({
                            "line": line,
                            "available": available_budget,
                            "required": line.amount,
                            "shortage": 0,
                            "valid": True
                        })
                
                # Determine overall validation status
                all_valid = all(result["valid"] for result in validation_results)
                transfer.has_sufficient_budget = all_valid
                
                # Generate validation message
                if not all_valid:
                    messages = []
                    for result in validation_results:
                        if not result["valid"]:
                            messages.append(
                                f"Account {result['line'].budget_account_id.code}: "
                                f"Available {result['available']:,.2f}, "
                                f"Required {result['required']:,.2f}, "
                                f"Shortage {result['shortage']:,.2f}"
                            )
                    transfer.budget_validation_message = "Insufficient budget:\n" + "\n".join(messages)
                else:
                    transfer.budget_validation_message = "Budget validation passed"
                    
            except Exception as e:
                transfer.has_sufficient_budget = False
                transfer.budget_validation_message = f"Validation error: {str(e)}"
    
    @api.onchange("date")
    def _onchange_date(self):
        """Auto-populate fiscal year based on date"""
        if self.date:
            fiscal_year = self.env["account.fiscal.year"].search([
                ("date_from", "<=", self.date),
                ("date_to", ">=", self.date),
                ("company_id", "=", self.company_id.id)
            ], limit=1)
            if fiscal_year:
                self.date_range_fy_id = fiscal_year
    
    # Workflow Actions
    def action_submit(self):
        """Submit transfer for approval"""
        self._validate_transfer_data()
        self._validate_budget_availability()
        
        self.write({
            "state": "submitted"
        })
        
        # Send notification to approvers
        self._notify_approvers()
        
        return True
    
    def action_approve(self):
        """Approve the transfer"""
        if not self.env.user.has_group("budget.group_budget_transfer_approver"):
            raise UserError(_("You don't have permission to approve budget transfers"))
        
        # Final validation before approval
        self._validate_budget_availability()
        
        self.write({
            "state": "approved",
            "approver_id": self.env.user.id,
            "approval_date": fields.Datetime.now(),
        })
        
        # Notify requestor
        self._notify_approval()
        
        return True
    
    def action_reject(self):
        """Reject the transfer with reason"""
        if not self.env.user.has_group("budget.group_budget_transfer_approver"):
            raise UserError(_("You don't have permission to reject budget transfers"))
        
        # Open wizard for rejection reason
        return self._open_rejection_wizard()
    
    def action_post(self):
        """Post the transfer and create budget moves"""
        if not self.env.user.has_group("budget.group_budget_transfer_manager"):
            raise UserError(_("You don't have permission to post budget transfers"))
        
        # Final validation before posting
        self._validate_budget_availability()
        
        # Create budget moves
        self._create_budget_moves()
        
        self.write({
            "state": "posted"
        })
        
        # Notify completion
        self._notify_completion()
        
        return True
    
    def action_cancel(self):
        """Cancel the transfer"""
        if self.state == "posted":
            raise UserError(_("Cannot cancel a posted transfer"))
        
        self.write({
            "state": "cancelled"
        })
        
        return True
    
    def action_reset_to_draft(self):
        """Reset transfer to draft state"""
        if not self.env.user.has_group("budget.group_budget_transfer_manager"):
            raise UserError(_("You don't have permission to reset budget transfers"))
        
        # Remove any generated budget moves if not posted
        if self.state != "posted":
            self.budget_move_ids.unlink()
        
        self.write({
            "state": "draft",
            "approver_id": False,
            "approval_date": False,
            "rejection_reason": False,
        })
        
        return True
    
    # Validation Methods
    def _validate_transfer_data(self):
        """Validate transfer data before submission"""
        self.ensure_one()
        
        if not self.line_ids:
            raise ValidationError(_("Please add transfer lines"))
        
        # Validate balanced transfer
        from_amount = sum(self.line_ids.filtered(lambda l: l.transfer_direction == "from").mapped("amount"))
        to_amount = sum(self.line_ids.filtered(lambda l: l.transfer_direction == "to").mapped("amount"))
        
        if abs(from_amount - to_amount) > 0.01:  # Allow small rounding differences
            raise ValidationError(_(
                "Transfer must be balanced. From amount: {}, To amount: {}"
            ).format(from_amount, to_amount))
        
        if from_amount != self.amount:
            raise ValidationError(_(
                "Transfer amount ({}) doesn't match line totals ({})"
            ).format(self.amount, from_amount))
    
    def _validate_budget_availability(self):
        """Validate budget availability for all source accounts"""
        self.ensure_one()
        
        if not self.has_sufficient_budget:
            raise ValidationError(_(
                "Insufficient budget for transfer:\n{}"
            ).format(self.budget_validation_message))
    
    # Budget Move Creation
    def _create_budget_moves(self):
        """Create budget moves for the transfer"""
        self.ensure_one()
        
        # Create a single budget move for the transfer
        move_vals = {
            "move_type": "entry",
            "date": self.date,
            "ref": f"Transfer: {self.name}",
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "journal_id": self._get_transfer_journal().id,
            "transfer_id": self.id,
        }
        
        budget_move = self.env["budget.move"].create(move_vals)
        
        # Create move lines for each transfer line
        for line in self.line_ids:
            line_vals = {
                "move_id": budget_move.id,
                "budget_account_id": line.budget_account_id.id,
                "analytic_distribution": line.analytic_distribution,
                "name": line.description or f"Transfer {line.transfer_direction}",
                "debit": line.amount if line.transfer_direction == "to" else 0,
                "credit": line.amount if line.transfer_direction == "from" else 0,
                "balance": line.amount if line.transfer_direction == "to" else -line.amount,
            }
            
            self.env["budget.move.line"].create(line_vals)
        
        # Post the budget move immediately
        budget_move.action_review()
        budget_move.action_post()
        
        return budget_move
    
    def _get_transfer_journal(self):
        """Get or create budget transfer journal"""
        journal = self.env["budget.journal"].search([
            ("code", "=", "BTRF"),
            ("company_id", "=", self.company_id.id)
        ], limit=1)
        
        if not journal:
            journal = self.env["budget.journal"].create({
                "name": "Budget Transfer",
                "code": "BTRF",
                "company_id": self.company_id.id,
                "default_budget_type": "expense",  # Default type
            })
        
        return journal
    
    # Notification Methods
    def _notify_approvers(self):
        """Send notification to budget transfer approvers"""
        approvers = self.env["res.users"].search([
            ("groups_id", "in", self.env.ref("budget.group_budget_transfer_approver").ids)
        ])
        
        if approvers:
            # Send email using template
            template = self.env.ref("budget.email_template_budget_transfer_submitted")
            if template:
                for approver in approvers:
                    template.with_context(lang=approver.lang).send_mail(
                        self.id,
                        email_values={"email_to": approver.email},
                        force_send=True
                    )
            
            # Also post in chatter
            self.message_post(
                body=_("Budget transfer submitted for approval by {}").format(self.user_id.name),
                partner_ids=approvers.partner_id.ids,
                message_type="notification"
            )
    
    def _notify_approval(self):
        """Send approval notification to requestor"""
        # Send email using template
        template = self.env.ref("budget.email_template_budget_transfer_approved")
        if template and self.user_id.email:
            template.with_context(lang=self.user_id.lang).send_mail(
                self.id,
                email_values={"email_to": self.user_id.email},
                force_send=True
            )
        
        # Also post in chatter
        self.message_post(
            body=_("Budget transfer approved by {}").format(self.approver_id.name),
            partner_ids=[self.user_id.partner_id.id],
            message_type="notification"
        )
    
    def _notify_completion(self):
        """Send completion notification"""
        # Send email to requestor
        template = self.env.ref("budget.email_template_budget_transfer_posted")
        if template and self.user_id.email:
            template.with_context(lang=self.user_id.lang).send_mail(
                self.id,
                email_values={"email_to": self.user_id.email},
                force_send=True
            )
        
        # Also post in chatter
        self.message_post(
            body=_("Budget transfer posted successfully. Budget moves created."),
            partner_ids=[self.user_id.partner_id.id, self.approver_id.partner_id.id],
            message_type="notification"
        )
    
    def _open_rejection_wizard(self):
        """Open wizard for rejection reason"""
        return {
            "name": _("Reject Budget Transfer"),
            "type": "ir.actions.act_window",
            "res_model": "budget.transfer.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_transfer_id": self.id},
        }


class BudgetMove(models.Model):
    _inherit = "budget.move"
    
    # Link to budget transfer
    transfer_id = fields.Many2one(
        comodel_name="budget.transfer",
        string="Related Transfer",
        help="Budget transfer that generated this move",
        index=True,
        ondelete="set null",
    )