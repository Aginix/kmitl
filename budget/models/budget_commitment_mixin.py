import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date

_logger = logging.getLogger(__name__)


class BudgetCommitmentMixin(models.AbstractModel):
    """
    Budget Commitment Mixin - API Interface for Budget Commitment Integration
    
    Purpose:
        Provides a standardized interface for other modules to integrate with the budget
        commitment system. This mixin allows any model to create, validate, and manage
        budget commitments without directly depending on the budget.commitment model.
    
    Requirements:
        Models using this mixin MUST also inherit from 'analytic.distribution.mixin'
        to provide the required 4D analytic dimension fields:
        • activity_analytic_id
        • department_analytic_id  
        • fund_analytic_id
        • source_analytic_id
    
    Key Features:
        • Standard API methods for commitment operations
        • Automatic validation and error handling
        • Budget availability checking with detailed feedback
        • Direct integration with 4D analytic dimensions
        • Commitment lifecycle management
        • Consumption tracking interface
    
    Usage:
        Inherit BOTH mixins in any model that needs budget commitments:
        
        class PurchaseOrder(models.Model):
            _name = 'purchase.order'
            _inherit = ['analytic.distribution.mixin', 'budget.commitment.mixin']
            
            budget_account_id = fields.Many2one(
                'budget.account',
                string='Budget Account',
                domain=[('budgetable', '=', True)]
            )
            
            def action_confirm(self):
                # Create budget commitment using model's analytic fields
                commitment = self._create_budget_commitment_from_record(
                    amount=self.amount_total,
                    budget_account_id=self.budget_account_id
                )
                self.budget_commitment_id = commitment
                return super().action_confirm()
    
    Integration Points:
        • Purchase Orders: Reserve budget when PO is confirmed
        • Expense Claims: Reserve budget for employee expenses  
        • Payment Requests: Reserve budget for pending payments
        • Project Tasks: Reserve budget for project activities
        • Any custom module requiring budget control
    """
    _name = 'budget.commitment.mixin'
    _description = 'Budget Commitment Mixin'
    
    # Optional field to link to commitment (implement in inheriting model if needed)
    # budget_commitment_id = fields.Many2one('budget.commitment', string='Budget Commitment')
    
    # Budget account field (implement in inheriting model)
    # budget_account_id = fields.Many2one('budget.account', string='Budget Account')
    
    def _validate_analytic_mixin(self):
        """
        Validate that the model inherits from analytic.distribution.mixin
        """
        if 'analytic.distribution.mixin' not in self._inherit and \
           not hasattr(self, 'activity_analytic_id'):
            raise ValidationError(_(
                "Model %s must inherit from 'analytic.distribution.mixin' to use budget.commitment.mixin"
            ) % self._name)
    
    @api.model
    def _prepare_commitment_values_from_record(self, record, amount, budget_account_id, 
                                              ref=None, description=None, **kwargs):
        """
        Prepare commitment values from a record that has analytic fields.
        
        Args:
            record: Record with analytic dimension fields (from analytic.distribution.mixin)
            amount (float): Amount to commit
            budget_account_id: Budget account (record or ID)
            ref (str): Optional reference
            description (str): Optional description
            **kwargs: Additional optional fields (date, user_id, company_id, etc.)
            
        Returns:
            dict: Prepared values for budget.commitment creation
        """
        # Validate that record has required analytic fields
        if not hasattr(record, 'activity_analytic_id'):
            raise ValidationError(_(
                "Record must have analytic dimension fields from analytic.distribution.mixin"
            ))
        
        # Ensure budget account
        if not budget_account_id:
            raise ValidationError(_("Budget account is required for commitment"))
        
        account_id = budget_account_id.id if hasattr(budget_account_id, 'id') else budget_account_id
        
        # Validate required analytic dimensions
        if not record.activity_analytic_id:
            raise ValidationError(_("Activity dimension is required for budget commitment"))
        if not record.fund_analytic_id:
            raise ValidationError(_("Fund dimension is required for budget commitment"))
        
        # Build commitment values from record's analytic fields
        commitment_vals = {
            'amount': amount,
            'account_id': account_id,
            'activity_analytic_id': record.activity_analytic_id.id,
            'fund_analytic_id': record.fund_analytic_id.id,
            'department_analytic_id': record.department_analytic_id.id if record.department_analytic_id else False,
            'source_analytic_id': record.source_analytic_id.id if record.source_analytic_id else False,
        }
        
        # Add optional fields
        commitment_vals['ref'] = ref or getattr(record, 'name', False)
        commitment_vals['description'] = description or ''
        
        # Date and fiscal year
        commitment_date = kwargs.get('date', fields.Date.today())
        commitment_vals['date'] = commitment_date
        
        if not kwargs.get('date_range_fy_id'):
            # Auto-detect fiscal year from date
            company_id = kwargs.get('company_id', record.company_id.id if hasattr(record, 'company_id') else self.env.company.id)
            fiscal_year = self.env['account.fiscal.year'].search([
                ('date_from', '<=', commitment_date),
                ('date_to', '>=', commitment_date),
                ('company_id', '=', company_id)
            ], limit=1)
            if not fiscal_year:
                raise ValidationError(_(
                    "No fiscal year found for date %s"
                ) % commitment_date)
            commitment_vals['date_range_fy_id'] = fiscal_year.id
        else:
            commitment_vals['date_range_fy_id'] = kwargs['date_range_fy_id']
        
        # User and company
        commitment_vals['user_id'] = kwargs.get('user_id', 
                                               getattr(record, 'user_id', self.env.user).id if hasattr(record, 'user_id') else self.env.user.id)
        commitment_vals['company_id'] = kwargs.get('company_id',
                                                  record.company_id.id if hasattr(record, 'company_id') else self.env.company.id)
        
        return commitment_vals
    
    def _create_budget_commitment_from_record(self, amount, budget_account_id, 
                                             ref=None, description=None, 
                                             auto_reserve=True, **kwargs):
        """
        Create a budget commitment from the current record's analytic dimensions.
        
        Args:
            amount (float): Amount to commit
            budget_account_id: Budget account (record or ID)
            ref (str): Optional reference (defaults to record.name)
            description (str): Optional description
            auto_reserve (bool): Automatically reserve the commitment
            **kwargs: Additional optional fields
            
        Returns:
            budget.commitment: Created commitment record
            
        Raises:
            ValidationError: If required fields are missing or record doesn't have analytic fields
            UserError: If budget is insufficient
        """
        self.ensure_one()
        
        # Prepare values from current record
        commitment_vals = self._prepare_commitment_values_from_record(
            self, amount, budget_account_id, ref, description, **kwargs
        )
        
        # Create commitment
        commitment = self.env['budget.commitment'].create(commitment_vals)
        
        # Auto reserve if requested
        if auto_reserve:
            try:
                commitment.action_reserve()
            except UserError as e:
                # Delete the commitment if reservation fails
                commitment.unlink()
                raise UserError(_(
                    "Failed to reserve budget commitment: %s"
                ) % str(e))
        
        _logger.info(
            "Created budget commitment %s for %s amount %s",
            commitment.name,
            self._name,
            commitment.amount
        )
        
        return commitment
    
    def _check_budget_availability_from_record(self, amount, budget_account_id, **kwargs):
        """
        Check budget availability using the record's analytic dimensions.
        
        Args:
            amount (float): Amount to check
            budget_account_id: Budget account (record or ID)
            **kwargs: Optional overrides for date_range_fy_id, company_id
            
        Returns:
            dict: Budget availability information with keys:
                - available (float): Available budget amount
                - requested (float): Requested amount
                - is_sufficient (bool): True if budget is sufficient
                - status (str): 'sufficient', 'warning', or 'insufficient'
                - message (str): Human-readable status message
                - percentage (float): Percentage of available budget requested
        """
        self.ensure_one()
        
        # Validate analytic fields
        if not self.activity_analytic_id or not self.fund_analytic_id:
            raise ValidationError(_(
                "Activity and Fund dimensions are required to check budget availability"
            ))
        
        if not budget_account_id:
            raise ValidationError(_("Budget account is required to check availability"))
        
        account_id = budget_account_id.id if hasattr(budget_account_id, 'id') else budget_account_id
        
        # Get budget controller
        budget_controller = self.env['budget.controller']
        
        # Prepare analytic data from record
        analytic_data = {
            'account_id': account_id,
            'activity_analytic_id': self.activity_analytic_id.id,
            'department_analytic_id': self.department_analytic_id.id if self.department_analytic_id else False,
            'fund_analytic_id': self.fund_analytic_id.id,
            'source_analytic_id': self.source_analytic_id.id if self.source_analytic_id else False,
        }
        
        # Determine fiscal year
        if not kwargs.get('date_range_fy_id'):
            check_date = kwargs.get('date', fields.Date.today())
            company_id = kwargs.get('company_id', 
                                   self.company_id.id if hasattr(self, 'company_id') else self.env.company.id)
            fiscal_year = self.env['account.fiscal.year'].search([
                ('date_from', '<=', check_date),
                ('date_to', '>=', check_date),
                ('company_id', '=', company_id)
            ], limit=1)
            if not fiscal_year:
                raise ValidationError(_(
                    "No fiscal year found for date %s"
                ) % check_date)
            fy_id = fiscal_year.id
        else:
            fy_id = kwargs['date_range_fy_id']
        
        company_id = kwargs.get('company_id',
                               self.company_id.id if hasattr(self, 'company_id') else self.env.company.id)
        
        # Get available budget
        available = budget_controller.get_available_budget(
            analytic_data,
            fy_id,
            company_id
        )
        
        # Check if negative budget is allowed
        allow_negative = self.env['ir.config_parameter'].sudo().get_param(
            'budget.allow_negative', False
        )
        
        # Determine status
        if available >= amount:
            status = 'sufficient'
            is_sufficient = True
            message = _("Budget is sufficient for this commitment")
        elif available >= amount * 0.5 or (allow_negative and available >= 0):
            status = 'warning'
            is_sufficient = True if allow_negative else False
            message = _("Low budget warning - %.1f%% of available budget") % (
                (amount / available * 100) if available > 0 else 999
            )
        elif allow_negative:
            status = 'warning'
            is_sufficient = True
            message = _("This will create a negative budget balance")
        else:
            status = 'insufficient'
            is_sufficient = False
            message = _("Insufficient budget - only %.2f available") % available
        
        return {
            'available': available,
            'requested': amount,
            'is_sufficient': is_sufficient,
            'status': status,
            'message': message,
            'percentage': (amount / available * 100) if available > 0 else 999.99
        }
    
    def _cancel_budget_commitment(self, commitment):
        """
        Cancel a budget commitment and release the reserved budget.
        
        Args:
            commitment (budget.commitment): Commitment to cancel
            
        Returns:
            bool: True if successful
            
        Raises:
            UserError: If commitment cannot be cancelled
        """
        if not commitment:
            return True
            
        if commitment.state == 'done':
            raise UserError(_(
                "Cannot cancel commitment %s - it is already done"
            ) % commitment.name)
        
        if commitment.state == 'cancel':
            return True  # Already cancelled
        
        commitment.action_cancel()
        _logger.info("Cancelled budget commitment %s", commitment.name)
        
        return True
    
    def _close_budget_commitment(self, commitment):
        """
        Close a budget commitment (mark as done).
        This releases any unused budget back to the pool.
        
        Args:
            commitment (budget.commitment): Commitment to close
            
        Returns:
            bool: True if successful
            
        Raises:
            UserError: If commitment cannot be closed
        """
        if not commitment:
            return True
            
        if commitment.state == 'done':
            return True  # Already done
        
        if commitment.state != 'reserved':
            raise UserError(_(
                "Cannot close commitment %s - it must be in reserved state"
            ) % commitment.name)
        
        commitment.action_done()
        _logger.info(
            "Closed budget commitment %s - Released %.2f",
            commitment.name,
            commitment.remaining_amount
        )
        
        return True
    
    def _update_commitment_amount(self, commitment, new_amount):
        """
        Update commitment amount with validation.
        
        Args:
            commitment (budget.commitment): Commitment to update
            new_amount (float): New commitment amount
            
        Returns:
            bool: True if successful
            
        Raises:
            ValidationError: If new amount is invalid
            UserError: If budget is insufficient for increase
        """
        if not commitment:
            raise ValidationError(_("No commitment to update"))
        
        if commitment.state != 'reserved':
            raise UserError(_(
                "Can only update amount for reserved commitments"
            ))
        
        if new_amount <= 0:
            raise ValidationError(_("Commitment amount must be positive"))
        
        if new_amount < commitment.consumed_amount:
            raise ValidationError(_(
                "New amount (%.2f) cannot be less than consumed amount (%.2f)"
            ) % (new_amount, commitment.consumed_amount))
        
        # If increasing amount, check budget availability
        if new_amount > commitment.amount:
            increase = new_amount - commitment.amount
            
            # Create temporary record with commitment's analytics for checking
            temp_vals = {
                'activity_analytic_id': commitment.activity_analytic_id,
                'department_analytic_id': commitment.department_analytic_id,
                'fund_analytic_id': commitment.fund_analytic_id,
                'source_analytic_id': commitment.source_analytic_id,
            }
            
            # Use a simple namespace object for the check
            class TempRecord:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)
            
            temp_record = TempRecord(**temp_vals)
            
            # Check availability for the increase using commitment's analytics
            check_result = self._check_budget_availability_from_record.call(
                temp_record,
                increase,
                commitment.account_id,
                date_range_fy_id=commitment.date_range_fy_id.id,
                company_id=commitment.company_id.id
            )
            
            if not check_result['is_sufficient']:
                raise UserError(_(
                    "Insufficient budget to increase commitment: %s"
                ) % check_result['message'])
        
        old_amount = commitment.amount
        commitment.amount = new_amount
        
        _logger.info(
            "Updated commitment %s amount from %.2f to %.2f",
            commitment.name,
            old_amount,
            new_amount
        )
        
        return True
    
    def _get_commitment_info(self, commitment):
        """
        Get detailed information about a commitment.
        
        Args:
            commitment (budget.commitment): Commitment record
            
        Returns:
            dict: Commitment information with keys:
                - id (int): Commitment ID
                - name (str): Commitment number
                - ref (str): Reference
                - state (str): Current state
                - amount (float): Total amount
                - consumed (float): Consumed amount
                - remaining (float): Remaining amount
                - available_budget (float): Available budget
                - budget_status (str): Budget availability status
                - analytics (dict): Analytic dimension IDs
        """
        if not commitment:
            return {}
        
        return {
            'id': commitment.id,
            'name': commitment.name,
            'ref': commitment.ref or '',
            'state': commitment.state,
            'amount': commitment.amount,
            'consumed': commitment.consumed_amount,
            'remaining': commitment.remaining_amount,
            'available_budget': commitment.available_budget_amount,
            'budget_status': commitment.budget_availability_status,
            'analytics': {
                'account_id': commitment.account_id.id,
                'activity_id': commitment.activity_analytic_id.id,
                'department_id': commitment.department_analytic_id.id if commitment.department_analytic_id else False,
                'fund_id': commitment.fund_analytic_id.id,
                'source_id': commitment.source_analytic_id.id if commitment.source_analytic_id else False,
            }
        }
    
    def _consume_commitment_from_record(self, commitment, amount, reference=None):
        """
        Record consumption against a commitment using record's analytics.
        Creates a budget move to consume the committed amount.
        
        Args:
            commitment (budget.commitment): Commitment to consume from
            amount (float): Amount to consume
            reference (str): Optional reference for the consumption
            
        Returns:
            budget.move: Created budget move for consumption
            
        Raises:
            ValidationError: If amount exceeds remaining commitment
        """
        self.ensure_one()
        
        if not commitment:
            raise ValidationError(_("No commitment to consume"))
        
        if commitment.state != 'reserved':
            raise UserError(_(
                "Can only consume from reserved commitments"
            ))
        
        if amount > commitment.remaining_amount:
            raise ValidationError(_(
                "Cannot consume %.2f - only %.2f remaining in commitment"
            ) % (amount, commitment.remaining_amount))
        
        # Use commitment's analytics for the consumption
        move_vals = {
            'name': reference or _("Consumption of %s") % commitment.name,
            'date': fields.Date.today(),
            'commitment_id': commitment.id,
            'move_type': 'consume',
            'line_ids': [(0, 0, {
                'account_id': commitment.account_id.id,
                'balance': -amount,  # Negative for consumption
                'activity_analytic_id': commitment.activity_analytic_id.id,
                'department_analytic_id': commitment.department_analytic_id.id if commitment.department_analytic_id else False,
                'fund_analytic_id': commitment.fund_analytic_id.id,
                'source_analytic_id': commitment.source_analytic_id.id if commitment.source_analytic_id else False,
            })]
        }
        
        budget_move = self.env['budget.move'].create(move_vals)
        budget_move.action_post()
        
        _logger.info(
            "Consumed %.2f from commitment %s (%.2f remaining)",
            amount,
            commitment.name,
            commitment.remaining_amount
        )
        
        # Auto-close commitment if fully consumed
        if commitment.remaining_amount <= 0.01:  # Small tolerance for rounding
            self._close_budget_commitment(commitment)
        
        return budget_move
    
    # Backward compatibility methods (will be deprecated)
    
    @api.model
    def _prepare_commitment_values(self, values):
        """
        [DEPRECATED] Use _prepare_commitment_values_from_record instead.
        Legacy method for backward compatibility.
        """
        _logger.warning(
            "Method _prepare_commitment_values is deprecated. "
            "Use _prepare_commitment_values_from_record with record that has analytic fields."
        )
        
        # Convert to new format by creating temp record
        class TempRecord:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        # Create temp record with analytic IDs
        temp_record = TempRecord(
            activity_analytic_id=self.env['account.analytic.account'].browse(values.get('activity_analytic_id')),
            department_analytic_id=self.env['account.analytic.account'].browse(values.get('department_analytic_id')) if values.get('department_analytic_id') else False,
            fund_analytic_id=self.env['account.analytic.account'].browse(values.get('fund_analytic_id')),
            source_analytic_id=self.env['account.analytic.account'].browse(values.get('source_analytic_id')) if values.get('source_analytic_id') else False,
        )
        
        return self._prepare_commitment_values_from_record(
            temp_record,
            values['amount'],
            values['account_id'],
            ref=values.get('ref'),
            description=values.get('description'),
            date=values.get('date'),
            date_range_fy_id=values.get('date_range_fy_id'),
            user_id=values.get('user_id'),
            company_id=values.get('company_id')
        )
    
    @api.model
    def _create_budget_commitment(self, values, auto_reserve=True):
        """
        [DEPRECATED] Use _create_budget_commitment_from_record instead.
        Legacy method for backward compatibility.
        """
        _logger.warning(
            "Method _create_budget_commitment is deprecated. "
            "Use _create_budget_commitment_from_record with record that has analytic fields."
        )
        
        commitment_vals = self._prepare_commitment_values(values)
        commitment = self.env['budget.commitment'].create(commitment_vals)
        
        if auto_reserve:
            try:
                commitment.action_reserve()
            except UserError as e:
                commitment.unlink()
                raise UserError(_("Failed to reserve budget commitment: %s") % str(e))
        
        return commitment
    
    @api.model  
    def _check_budget_availability(self, values):
        """
        [DEPRECATED] Use _check_budget_availability_from_record instead.
        Legacy method for backward compatibility.
        """
        _logger.warning(
            "Method _check_budget_availability is deprecated. "
            "Use _check_budget_availability_from_record with record that has analytic fields."
        )
        
        # Create temp record for compatibility
        class TempRecord:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        temp_record = TempRecord(
            activity_analytic_id=self.env['account.analytic.account'].browse(values.get('activity_analytic_id')),
            department_analytic_id=self.env['account.analytic.account'].browse(values.get('department_analytic_id')) if values.get('department_analytic_id') else False,
            fund_analytic_id=self.env['account.analytic.account'].browse(values.get('fund_analytic_id')),
            source_analytic_id=self.env['account.analytic.account'].browse(values.get('source_analytic_id')) if values.get('source_analytic_id') else False,
        )
        
        return self._check_budget_availability_from_record.call(
            temp_record,
            values['amount'],
            values['account_id'],
            date=values.get('date'),
            date_range_fy_id=values.get('date_range_fy_id'),
            company_id=values.get('company_id')
        )
    
    @api.model
    def _consume_commitment(self, commitment, amount, reference=None):
        """
        [DEPRECATED] Use _consume_commitment_from_record instead.
        Legacy method for backward compatibility.
        """
        _logger.warning(
            "Method _consume_commitment is deprecated. "
            "Use _consume_commitment_from_record instead."
        )
        
        # Call the new method on a dummy record
        return self._consume_commitment_from_record(commitment, amount, reference)