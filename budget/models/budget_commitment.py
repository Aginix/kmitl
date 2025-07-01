import logging
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    _name = "budget.commitment"
    _description = "Budget Commitment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "ref"]

    READONLY_STATES = {
        "confirmed": [("readonly", True)],
        "reserved": [("readonly", True)],
        "consumed": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        string="Number",
        required=True,
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
        readonly=False,
        states=READONLY_STATES,
    )
    
    ref = fields.Char(
        string="Reference", 
        copy=False, 
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    
    date = fields.Date(
        string="Commitment Date",
        required=True,
        index=True,
        default=fields.Date.context_today,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("reserved", "Reserved"),
            ("consumed", "Consumed"), 
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )
    
    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    
    description = fields.Text(
        string="Description",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    
    # Analytic dimensions
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        required=True,
        store=True,
        copy=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
        domain=[("root_plan_id.code", "=", "departments")],
    )
    
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        required=True,
        store=True,
        copy=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
        domain=[("root_plan_id.code", "=", "sources")],
    )
    
    user_id = fields.Many2one(
        string="Responsible User",
        comodel_name="res.users",
        copy=False,
        default=lambda self: self.env.user,
        store=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    
    line_ids = fields.One2many(
        comodel_name="budget.commitment.line",
        inverse_name="commitment_id",
        string="Commitment Lines",
        copy=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        store=True,
    )
    
    # Computed fields
    total_amount = fields.Monetary(
        string="Total Amount",
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    
    consumed_amount = fields.Monetary(
        string="Consumed Amount", 
        compute="_compute_consumed_amount",
        store=True,
        currency_field="currency_id",
    )
    
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_remaining_amount", 
        store=True,
        currency_field="currency_id",
    )
    
    # Workflow control fields
    show_confirm_button = fields.Boolean(
        compute="_compute_show_buttons"
    )
    show_reserve_button = fields.Boolean(
        compute="_compute_show_buttons"
    )
    show_reset_to_draft_button = fields.Boolean(
        compute="_compute_show_buttons"
    )
    
    # Related budget moves for consumption tracking
    budget_move_ids = fields.One2many(
        comodel_name="budget.move",
        inverse_name="commitment_id",
        string="Related Budget Moves",
        readonly=True,
    )
    
    @api.depends("line_ids.amount")
    def _compute_amount(self):
        for record in self:
            record.total_amount = sum(line.amount for line in record.line_ids)
    
    @api.depends("budget_move_ids.line_ids.balance", "budget_move_ids.state")
    def _compute_consumed_amount(self):
        for record in self:
            consumed = 0.0
            for move in record.budget_move_ids.filtered(lambda m: m.state == "posted"):
                consumed += sum(line.balance for line in move.line_ids)
            record.consumed_amount = consumed
    
    @api.depends("total_amount", "consumed_amount")
    def _compute_remaining_amount(self):
        for record in self:
            record.remaining_amount = record.total_amount - record.consumed_amount
    
    @api.depends("state")
    def _compute_show_buttons(self):
        for record in self:
            record.show_confirm_button = record.state == "draft"
            record.show_reserve_button = record.state == "confirmed"
            record.show_reset_to_draft_button = record.state in ("confirmed", "cancel")
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("budget.commitment") or _("New")
        return super().create(vals_list)
    
    def action_confirm(self):
        """Confirm the commitment - validates data and makes it official"""
        self._validate_commitment()
        self.write({"state": "confirmed"})
        self.message_post(body=_("Commitment confirmed."))
    
    def action_reserve(self):
        """Reserve budget - checks budget availability and reserves amounts"""
        self._check_budget_availability()
        self.write({"state": "reserved"})
        self.message_post(body=_("Budget reserved for commitment."))
    
    def action_consume(self):
        """Mark as consumed - when budget moves are created against this commitment"""
        if self.remaining_amount <= 0:
            self.write({"state": "consumed"})
            self.message_post(body=_("Commitment fully consumed."))
        else:
            self.write({"state": "consumed"})
            self.message_post(body=_("Commitment partially consumed."))
    
    def create_consumption_move(self, amount=None):
        """Create a 'consume' type budget move for this commitment"""
        self.ensure_one()
        
        if not amount:
            amount = self.remaining_amount
        
        if amount <= 0:
            raise UserError(_("Cannot create consumption move with zero or negative amount."))
        
        if amount > self.remaining_amount:
            raise UserError(_("Cannot consume more than remaining amount."))
        
        # Create the budget move
        move_vals = {
            'move_type': 'consume',
            'commitment_id': self.id,
            'date': fields.Date.today(),
            'ref': _('Consumption of commitment %s') % self.name,
            'company_id': self.company_id.id,
            'date_range_fy_id': self.date_range_fy_id.id,
            'department_analytic_id': self.department_analytic_id.id if self.department_analytic_id else False,
            'source_analytic_id': self.source_analytic_id.id if self.source_analytic_id else False,
        }
        
        # Create move lines for each commitment line
        line_vals = []
        for commitment_line in self.line_ids:
            # Calculate proportional amount for this line
            line_amount = (commitment_line.amount / self.total_amount) * amount if self.total_amount else 0
            
            if line_amount > 0:
                line_vals.append((0, 0, {
                    'account_id': commitment_line.account_id.id,
                    'activity_analytic_id': commitment_line.activity_analytic_id.id if commitment_line.activity_analytic_id else False,
                    'fund_analytic_id': commitment_line.fund_analytic_id.id if commitment_line.fund_analytic_id else False,
                    'source_analytic_id': self.source_analytic_id.id if self.source_analytic_id else False,
                    'balance': line_amount,
                    'name': _('Consumption: %s') % commitment_line.name,
                }))
        
        move_vals['line_ids'] = line_vals
        
        # Create and post the move
        budget_move = self.env['budget.move'].create(move_vals)
        budget_move.action_post()
        
        # Update commitment state if fully consumed
        if self.remaining_amount <= 0:
            self.action_consume()
        
        return budget_move
    
    def action_create_consumption_move(self):
        """Button action to create consumption move"""
        self.ensure_one()
        if self.remaining_amount <= 0:
            raise UserError(_("No remaining amount to consume."))
        
        move = self.create_consumption_move()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Consumption Move'),
            'res_model': 'budget.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_done(self):
        """Complete the commitment process"""
        self.write({"state": "done"})
        self.message_post(body=_("Commitment completed."))
    
    def action_cancel(self):
        """Cancel the commitment"""
        if self.consumed_amount > 0:
            raise UserError(_("Cannot cancel commitment that has been consumed."))
        self.write({"state": "cancel"})
        self.message_post(body=_("Commitment cancelled."))
    
    def action_reset_to_draft(self):
        """Reset to draft state"""
        if self.consumed_amount > 0:
            raise UserError(_("Cannot reset commitment that has been consumed."))
        self.write({"state": "draft"})
        self.message_post(body=_("Commitment reset to draft."))
    
    def _validate_commitment(self):
        """Validate commitment data before confirmation"""
        if not self.line_ids:
            raise ValidationError(_("Commitment must have at least one line."))
        
        if self.total_amount <= 0:
            raise ValidationError(_("Total commitment amount must be positive."))
        
        for line in self.line_ids:
            if line.amount <= 0:
                raise ValidationError(_("All commitment line amounts must be positive."))
    
    def _check_budget_availability(self):
        """Check if sufficient budget is available for this commitment"""
        self.ensure_one()
        _logger.info("Checking budget availability for commitment %s", self.name)
        
        validation_errors = []
        
        for line in self.line_ids:
            available_amount = self._get_available_budget_amount(line)
            requested_amount = line.amount
            
            if requested_amount > available_amount:
                error_msg = _(
                    "Insufficient budget for line '%(line_name)s':\n"
                    "- Budget Account: %(account)s\n"
                    "- Activity: %(activity)s\n"
                    "- Department: %(department)s\n"
                    "- Fund: %(fund)s\n"
                    "- Source: %(source)s\n"
                    "- Available: %(available).2f\n"
                    "- Requested: %(requested).2f\n"
                    "- Shortage: %(shortage).2f"
                ) % {
                    'line_name': line.name,
                    'account': line.account_id.display_name,
                    'activity': line.activity_analytic_id.display_name,
                    'department': line.department_analytic_id.display_name,
                    'fund': line.fund_analytic_id.display_name,
                    'source': line.source_analytic_id.display_name,
                    'available': available_amount,
                    'requested': requested_amount,
                    'shortage': requested_amount - available_amount,
                }
                validation_errors.append(error_msg)
        
        if validation_errors:
            raise ValidationError("\n\n".join(validation_errors))
        
        return True
    
    def _get_available_budget_amount(self, line):
        """Get available budget amount for a commitment line"""
        # Calculate: Appropriated - Reserved - Consumed
        appropriated = self._calculate_appropriated_amount(line)
        reserved = self._calculate_reserved_amount(line)
        consumed = self._calculate_consumed_amount(line)
        
        available = appropriated - reserved - consumed
        return max(0.0, available)  # Never return negative
    
    def _calculate_appropriated_amount(self, line):
        """Calculate total appropriated budget for this line's analytic combination"""
        BudgetMove = self.env['budget.move']
        
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'appropriation'),
            ('date_range_fy_id', '=', self.date_range_fy_id.id),
            ('company_id', '=', self.company_id.id),
        ]
        
        moves = BudgetMove.search(domain)
        total = 0.0
        
        for move in moves:
            for move_line in move.line_ids.filtered(lambda l: not l.is_virtual_line):
                if self._line_matches_analytic_combination(move_line, line):
                    total += abs(move_line.balance)
        
        return total
    
    def _calculate_reserved_amount(self, line):
        """Calculate total reserved amount from other commitments"""
        BudgetCommitment = self.env['budget.commitment']
        
        domain = [
            ('state', '=', 'reserved'),
            ('date_range_fy_id', '=', self.date_range_fy_id.id),
            ('company_id', '=', self.company_id.id),
            ('id', '!=', self.id),  # Exclude current commitment
        ]
        
        commitments = BudgetCommitment.search(domain)
        total = 0.0
        
        for commitment in commitments:
            for commitment_line in commitment.line_ids:
                if self._line_matches_analytic_combination(commitment_line, line):
                    total += commitment_line.remaining_amount
        
        return total
    
    def _calculate_consumed_amount(self, line):
        """Calculate total consumed amount from budget moves"""
        BudgetMove = self.env['budget.move']
        
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'consume'),
            ('date_range_fy_id', '=', self.date_range_fy_id.id),
            ('company_id', '=', self.company_id.id),
        ]
        
        moves = BudgetMove.search(domain)
        total = 0.0
        
        for move in moves:
            for move_line in move.line_ids.filtered(lambda l: not l.is_virtual_line):
                if self._line_matches_analytic_combination(move_line, line):
                    total += abs(move_line.balance)
        
        return total
    
    def _line_matches_analytic_combination(self, move_line, commitment_line):
        """Check if move line matches commitment line's analytic combination"""
        # Exact match for budget account and source (no hierarchy)
        if (move_line.account_id != commitment_line.account_id or
            move_line.source_analytic_id != commitment_line.source_analytic_id):
            return False
        
        # For activities, departments, and funds, check hierarchical relationships
        activity_match = self._analytic_accounts_match_hierarchical(
            move_line.activity_analytic_id, commitment_line.activity_analytic_id
        )
        department_match = self._analytic_accounts_match_hierarchical(
            move_line.department_analytic_id, commitment_line.department_analytic_id
        )
        fund_match = self._analytic_accounts_match_hierarchical(
            move_line.fund_analytic_id, commitment_line.fund_analytic_id
        )
        
        return activity_match and department_match and fund_match
    
    def _analytic_accounts_match_hierarchical(self, move_account, commitment_account):
        """
        Check if analytic accounts match hierarchically.
        
        For appropriations: move_account (parent) can provide budget for commitment_account (child)
        For commitments/consumption: exact match required
        
        Args:
            move_account: Analytic account from move line (could be parent providing budget)
            commitment_account: Analytic account from commitment line (could be child needing budget)
        
        Returns:
            bool: True if accounts match hierarchically
        """
        # Handle None cases
        if not move_account and not commitment_account:
            return True
        if not move_account or not commitment_account:
            return False
        
        # Exact match
        if move_account.id == commitment_account.id:
            return True
        
        # Check if move_account is a parent of commitment_account
        # This allows parent-level appropriations to cover child-level commitments
        if commitment_account.parent_path and move_account.id:
            # Extract parent IDs from commitment_account's parent_path
            parent_ids = self._get_parent_ids_from_path(commitment_account.parent_path)
            return move_account.id in parent_ids
        
        return False
    
    def _get_parent_ids_from_path(self, parent_path):
        """Extract parent IDs from parent_path field"""
        if not parent_path:
            return []
        
        # parent_path format: "1/2/3/" - extract all IDs
        path_parts = parent_path.strip('/').split('/')
        return [int(id_str) for id_str in path_parts if id_str.isdigit()]
    
    @api.constrains("date", "date_range_fy_id")
    def _check_date_in_fiscal_year(self):
        """Ensure commitment date falls within the fiscal year"""
        for record in self:
            if record.date_range_fy_id:
                fy = record.date_range_fy_id
                if not (fy.date_from <= record.date <= fy.date_to):
                    raise ValidationError(
                        _("Commitment date must be within the selected fiscal year (%s - %s).")
                        % (fy.date_from, fy.date_to)
                    )
    
    def action_view_budget_moves(self):
        """View related budget moves"""
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Budget Moves for %s') % self.name,
            'res_model': 'budget.move',
            'view_mode': 'tree,form',
            'domain': [('commitment_id', '=', self.id)],
            'context': {
                'default_commitment_id': self.id,
                'default_department_analytic_id': self.department_analytic_id.id,
                'default_source_analytic_id': self.source_analytic_id.id,
            }
        }
        return action
    
    def action_check_budget_availability(self):
        """Check budget availability for all lines and show results"""
        self.ensure_one()
        
        # Force recomputation of availability
        self.line_ids._compute_available_budget()
        
        insufficient_lines = self.line_ids.filtered(lambda l: l.budget_availability_status == 'insufficient')
        warning_lines = self.line_ids.filtered(lambda l: l.budget_availability_status == 'warning')
        
        if insufficient_lines:
            message = _("Budget Check Failed!\n\nThe following lines have insufficient budget:\n\n")
            for line in insufficient_lines:
                message += _("• %(account)s - %(activity)s - %(fund)s\n"
                           "  Requested: %(requested)s, Available: %(available)s\n\n") % {
                    'account': line.account_id.display_name,
                    'activity': line.activity_analytic_id.display_name,
                    'fund': line.fund_analytic_id.display_name,
                    'requested': "{:,.2f}".format(line.amount),
                    'available': "{:,.2f}".format(line.available_budget_amount),
                }
            
            raise UserError(message)
        
        elif warning_lines:
            message = _("Budget Check - Warnings Found\n\n")
            message += _("All lines have sufficient budget, but the following lines will use more than 50%% of available budget:\n\n")
            for line in warning_lines:
                message += _("• %(account)s - %(percentage).1f%% of available budget\n") % {
                    'account': line.account_id.display_name,
                    'percentage': line.budget_availability_percentage,
                }
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Budget Check - Warnings'),
                    'message': message,
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Budget Check Passed'),
                    'message': _('All commitment lines have sufficient budget available.'),
                    'type': 'success',
                    'sticky': False,
                }
            }