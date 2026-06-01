import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

_logger = logging.getLogger(__name__)


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

    can_edit = fields.Boolean(compute="_compute_can_edit")

    @api.depends("state")
    def _compute_can_edit(self):
        for rec in self:
            rec.can_edit = rec.state == "draft"

    # Transfer Details
    transfer_type = fields.Selection(
        selection=[
            ("entry", "ทั่วไป"),
        ],
        string="Transfer Type",
        required=True,
        default="entry",
        readonly=True,
        tracking=True,
    )

    amount = fields.Float(
        string="Transfer Amount",
        compute="_compute_amount",
        store=True,
        digits="Budget Precision",
        readonly=True,
        tracking=True,
    )

    reason = fields.Text(
        string="Transfer Reason",
        required=True,
        readonly=False,
        states=READONLY_STATES,
        tracking=True,
        help="Please provide detailed justification for this budget transfer",
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
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    # Analytics at transfer level
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        domain=[("root_plan_id.code", "=", "departments")],
        required=True,
        readonly=False,
        states=READONLY_STATES,
        tracking=True,
        help="Department for this transfer",
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
        required=True,
        readonly=False,
        states=READONLY_STATES,
        tracking=True,
        help="Source of funds for this transfer",
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

    # Separate FROM and TO lines for better UX
    from_line_ids = fields.One2many(
        comodel_name="budget.transfer.line",
        inverse_name="transfer_id",
        string="Transfer FROM Lines",
        domain=[("transfer_direction", "=", "from")],
        context={"default_transfer_direction": "from"},
        copy=False,
        readonly=False,
        states=READONLY_STATES,
    )

    to_line_ids = fields.One2many(
        comodel_name="budget.transfer.line",
        inverse_name="transfer_id",
        string="Transfer TO Lines",
        domain=[("transfer_direction", "=", "to")],
        context={"default_transfer_direction": "to"},
        copy=False,
        readonly=False,
        states=READONLY_STATES,
    )

    # Generated Budget Moves
    budget_move_ids = fields.One2many(
        comodel_name="budget.move",
        inverse_name="transfer_id",
        string="Generated Budget Moves",
        readonly=True,
        help="Budget moves created when this transfer is posted",
    )

    # Button Visibility
    show_submit_button = fields.Boolean(compute="_compute_button_visibility")
    show_approve_button = fields.Boolean(compute="_compute_button_visibility")
    show_reject_button = fields.Boolean(compute="_compute_button_visibility")
    show_post_button = fields.Boolean(compute="_compute_button_visibility")
    show_cancel_button = fields.Boolean(compute="_compute_button_visibility")
    show_reset_button = fields.Boolean(compute="_compute_button_visibility")

    # Validation Fields
    has_sufficient_budget = fields.Boolean(
        compute="_compute_budget_validation",
        help="Indicates if source has sufficient budget for transfer",
    )

    budget_validation_message = fields.Text(
        compute="_compute_budget_validation", help="Detailed budget validation message"
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
                transfer.name = self.env["ir.sequence"].next_by_code(
                    "budget.transfer"
                ) or _("New")

    @api.depends("state", "user_id")
    def _compute_button_visibility(self):
        """Control button visibility based on state and user permissions"""
        for transfer in self:
            user = self.env.user

            # Submit button - only in draft state for requestor
            transfer.show_submit_button = (
                transfer.state == "draft" and transfer.user_id == user
            )

            # Approve/Reject buttons - available for all users in submitted state
            transfer.show_approve_button = transfer.state == "submitted"
            transfer.show_reject_button = transfer.state == "submitted"

            # Post button - available for all users in approved state
            transfer.show_post_button = transfer.state == "approved"

            # Cancel button - available in draft/submitted states
            transfer.show_cancel_button = transfer.state in ("draft", "submitted")

            # Reset button - available for all users in non-draft states
            transfer.show_reset_button = transfer.state != "draft"

    @api.depends("line_ids.amount")
    def _compute_amount(self):
        """
        Compute total transfer amount from FROM lines.

        The transfer amount is based on the total amount being transferred FROM
        source accounts. This should match the total TO amount for a balanced transfer.

        Business Logic:
        - Only count 'from' direction lines to avoid double counting
        - This represents the total budget being moved
        - TO lines should sum to the same amount for validation
        """
        for transfer in self:
            from_amount = sum(
                transfer.line_ids.filtered(
                    lambda l: l.transfer_direction == "from"
                ).mapped("amount")
            )
            transfer.amount = from_amount

    @api.depends("line_ids", "amount", "state")
    def _compute_budget_validation(self):
        """
        Validate budget availability for transfer lines.

        This method checks if there's sufficient budget available in all source
        accounts before allowing the transfer to proceed.

        Validation Process:
        1. Skip validation for posted/cancelled transfers
        2. For each FROM line, check available budget using BudgetController
        3. Compare available vs required amounts
        4. Generate detailed validation messages
        5. Set overall validation status

        Integration with BudgetController:
        - Uses analytic_data format expected by budget.controller
        - Includes all analytic dimensions (activity, department, fund, source, account)
        - Considers fiscal year and company context
        """
        for transfer in self:
            if not transfer.line_ids or transfer.state in ("posted", "cancelled"):
                transfer.has_sufficient_budget = True
                transfer.budget_validation_message = ""
                continue

            try:
                # Validate each line's budget availability
                validation_results = []

                for line in transfer.line_ids.filtered(
                    lambda l: l.transfer_direction == "from"
                ):
                    # Check budget availability using budget controller
                    budget_controller = self.env["budget.controller"]

                    # Build analytic data for budget controller
                    # Note: BudgetController expects analytic_data dict with specific keys
                    analytic_data = {}
                    if line.activity_analytic_id:
                        analytic_data["activity_analytic_id"] = (
                            line.activity_analytic_id.id
                        )
                    if line.department_analytic_id:
                        analytic_data["department_analytic_id"] = (
                            line.department_analytic_id.id
                        )
                    if line.fund_analytic_id:
                        analytic_data["fund_analytic_id"] = line.fund_analytic_id.id
                    if line.source_analytic_id:
                        analytic_data["source_analytic_id"] = line.source_analytic_id.id
                    if line.budget_account_id:
                        analytic_data["account_id"] = line.budget_account_id.id

                    available_budget = budget_controller.get_available_budget(
                        analytic_data=analytic_data,
                        fiscal_year_id=(
                            transfer.account_fiscal_year_id.id
                            if transfer.account_fiscal_year_id
                            else False
                        ),
                        company_id=transfer.company_id.id,
                    )

                    if available_budget < line.amount:
                        shortage = line.amount - available_budget
                        validation_results.append(
                            {
                                "line": line,
                                "available": available_budget,
                                "required": line.amount,
                                "shortage": shortage,
                                "valid": False,
                            }
                        )
                    else:
                        validation_results.append(
                            {
                                "line": line,
                                "available": available_budget,
                                "required": line.amount,
                                "shortage": 0,
                                "valid": True,
                            }
                        )

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
                    transfer.budget_validation_message = (
                        "Insufficient budget:\n" + "\n".join(messages)
                    )
                else:
                    transfer.budget_validation_message = "Budget validation passed"

            except Exception as e:
                transfer.has_sufficient_budget = False
                transfer.budget_validation_message = f"Validation error: {str(e)}"

    @api.onchange("date")
    def _onchange_date(self):
        """Auto-populate fiscal year based on date"""
        if self.date:
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", self.date),
                    ("date_to", ">=", self.date),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if fiscal_year:
                self.account_fiscal_year_id = fiscal_year

    @api.onchange("line_ids")
    def _onchange_line_ids(self):
        """Validate balance when lines change"""
        if self.line_ids:
            from_lines = self.line_ids.filtered(
                lambda l: l.transfer_direction == "from"
            )
            to_lines = self.line_ids.filtered(lambda l: l.transfer_direction == "to")

            from_amount = sum(from_lines.mapped("amount"))
            to_amount = sum(to_lines.mapped("amount"))

            if (
                from_amount > 0
                and to_amount > 0
                and abs(from_amount - to_amount) > 0.01
            ):
                return {
                    "warning": {
                        "title": _("Unbalanced Transfer"),
                        "message": _(
                            "From amount ({:,.2f}) doesn't match To amount ({:,.2f}). "
                            "Please ensure the transfer is balanced."
                        ).format(from_amount, to_amount),
                    }
                }

    # Workflow Actions
    def action_submit(self):
        """Submit transfer for approval"""
        self._validate_transfer_data()
        self._validate_budget_availability()

        self.write({"state": "submitted"})

        # Send notification to approvers
        # self._notify_approvers()

        return True

    def action_approve(self):
        """Approve the transfer"""
        # Check permission - only Budget Manager can approve
        if not self.env.user.has_group("budget.group_budget_manager"):
            raise UserError(
                _("Only Budget Managers can approve transfers")
            )

        # Final validation before approval
        self._validate_budget_availability()

        self.write(
            {
                "state": "approved",
                "approver_id": self.env.user.id,
                "approval_date": fields.Datetime.now(),
            }
        )

        # Notify requestor
        # self._notify_approval()

        return True

    def action_reject(self):
        """Reject the transfer with reason"""
        # Check permission - only Budget Manager can reject
        if not self.env.user.has_group("budget.group_budget_manager"):
            raise UserError(
                _("Only Budget Managers can reject transfers")
            )

        # Open wizard for rejection reason
        return self._open_rejection_wizard()

    def action_post(self):
        """Post the transfer and create budget moves"""
        # Check permission - only Budget Manager can post
        if not self.env.user.has_group("budget.group_budget_manager"):
            raise UserError(
                _("Only Budget Managers can post transfers")
            )

        # Final validation before posting
        self._validate_budget_availability()

        # Create budget moves
        self._create_budget_moves()

        self.write({"state": "posted"})

        # Notify completion
        # self._notify_completion()

        return True

    def action_cancel(self):
        """Cancel the transfer"""
        if self.state == "posted":
            raise UserError(_("Cannot cancel a posted transfer"))

        self.write({"state": "cancelled"})

        return True

    def action_reset_to_draft(self):
        """Reset transfer to draft state"""
        # Remove any generated budget moves if not posted
        if self.state != "posted":
            self.budget_move_ids.unlink()

        self.write(
            {
                "state": "draft",
                "approver_id": False,
                "approval_date": False,
                "rejection_reason": False,
            }
        )

        return True

    # Validation Methods
    def _validate_transfer_data(self):
        """Validate transfer data before submission"""
        self.ensure_one()

        if not self.line_ids:
            raise ValidationError(_("Please add transfer lines"))

        # Check for both FROM and TO lines
        from_lines = self.line_ids.filtered(lambda l: l.transfer_direction == "from")
        to_lines = self.line_ids.filtered(lambda l: l.transfer_direction == "to")

        if not from_lines:
            raise ValidationError(
                _("Please add at least one source line (Transfer FROM)")
            )

        if not to_lines:
            raise ValidationError(
                _("Please add at least one destination line (Transfer TO)")
            )

        # Validate balanced transfer
        from_amount = sum(from_lines.mapped("amount"))
        to_amount = sum(to_lines.mapped("amount"))

        if abs(from_amount - to_amount) > 0.01:  # Allow small rounding differences
            raise ValidationError(
                _(
                    "Transfer must be balanced. From amount: {:,.2f}, To amount: {:,.2f}"
                ).format(from_amount, to_amount)
            )

        if from_amount <= 0:
            raise ValidationError(_("Transfer amount must be greater than zero"))

    def _validate_budget_availability(self):
        """Validate budget availability for all source accounts"""
        self.ensure_one()

        if not self.has_sufficient_budget:
            raise ValidationError(
                _("Insufficient budget for transfer:\n{}").format(
                    self.budget_validation_message
                )
            )

    def _prepare_budget_move_vals(self):
        return {
            "move_type": "entry",
            "date": self.date,
            "ref": _(f"Transfer: {self.name}"),
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "transfer_id": self.id,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
        }

    # Budget Move Creation
    def _create_budget_moves(self):
        """Create budget moves for the transfer"""
        self.ensure_one()

        # Validate that we have balanced lines before creating moves
        from_total = sum(
            self.line_ids.filtered(lambda l: l.transfer_direction == "from").mapped(
                "amount"
            )
        )
        to_total = sum(
            self.line_ids.filtered(lambda l: l.transfer_direction == "to").mapped(
                "amount"
            )
        )

        if abs(from_total - to_total) > 0.01:
            raise ValidationError(
                _("Transfer lines are not balanced. FROM: {:,.2f}, TO: {:,.2f}").format(
                    from_total, to_total
                )
            )

        budget_move = self.env["budget.move"].create(self._prepare_budget_move_vals())

        # Collect all move line data first, then create in batch
        move_lines_data = []
        total_debits = 0.0
        total_credits = 0.0

        for line in self.line_ids:
            # In budget accounting: FROM (source) = Credit, TO (destination) = Debit
            # This represents money flowing FROM source accounts TO destination accounts
            debit_amount = line.amount if line.transfer_direction == "to" else 0.0
            credit_amount = line.amount if line.transfer_direction == "from" else 0.0
            balance_amount = (
                line.amount if line.transfer_direction == "to" else -line.amount
            )

            total_debits += debit_amount
            total_credits += credit_amount

            line_vals = {
                "move_id": budget_move.id,
                "account_id": line.budget_account_id.id,
                "analytic_distribution": line.analytic_distribution,
                "activity_analytic_id": line.activity_analytic_id.id,
                "department_analytic_id": line.department_analytic_id.id,
                "fund_analytic_id": line.fund_analytic_id.id,
                "source_analytic_id": line.source_analytic_id.id,
                "name": line.description
                or f"Transfer {line.transfer_direction.upper()}",
                "debit": debit_amount,
                "credit": credit_amount,
                "balance": balance_amount,
            }

            move_lines_data.append(line_vals)

        # Validate the move is balanced before creating lines
        if abs(total_debits - total_credits) > 0.01:
            raise ValidationError(
                _(
                    "Budget move is not balanced. Total debits: {:,.2f}, Total credits: {:,.2f}"
                ).format(total_debits, total_credits)
            )

        # Create all move lines in a single batch transaction
        self.env["budget.move.line"].create(move_lines_data)

        # Post the budget move immediately
        budget_move.action_review()
        budget_move.action_post()

        return budget_move

    # Notification Methods
    def _notify_approvers(self):
        """Send notification to budget transfer approvers"""
        # Send email using template to all users
        template = self.env.ref("budget.email_template_budget_transfer_submitted")
        if template:
            # Get all active users as potential approvers
            users = self.env["res.users"].search([("active", "=", True)])
            for user in users:
                if user.email:
                    template.with_context(lang=user.lang).send_mail(
                        self.id,
                        email_values={"email_to": user.email},
                        force_send=True,
                    )

        # Also post in chatter
        self.message_post(
            body=_("Budget transfer submitted for approval by {}").format(
                self.user_id.name
            ),
            message_type="notification",
        )

    def _notify_approval(self):
        """Send approval notification to requestor"""
        # Send email using template
        template = self.env.ref("budget.email_template_budget_transfer_approved")
        if template and self.user_id.email:
            template.with_context(lang=self.user_id.lang).send_mail(
                self.id, email_values={"email_to": self.user_id.email}, force_send=True
            )

        # Also post in chatter
        self.message_post(
            body=_("Budget transfer approved by {}").format(self.approver_id.name),
            partner_ids=[self.user_id.partner_id.id],
            message_type="notification",
        )

    def _notify_completion(self):
        """Send completion notification"""
        # Send email to requestor
        template = self.env.ref("budget.email_template_budget_transfer_posted")
        if template and self.user_id.email:
            template.with_context(lang=self.user_id.lang).send_mail(
                self.id, email_values={"email_to": self.user_id.email}, force_send=True
            )

        # Also post in chatter
        self.message_post(
            body=_("Budget transfer posted successfully. Budget moves created."),
            partner_ids=[self.user_id.partner_id.id, self.approver_id.partner_id.id],
            message_type="notification",
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
