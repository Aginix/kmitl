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

    Features:
        • Dynamic field configuration for maximum flexibility
        • Parameter-based API for analytic dimensions
        • Budget availability checking with detailed feedback
        • Commitment lifecycle management

    Key Features:
        • Standard API methods for commitment operations
        • Automatic validation and error handling
        • Budget availability checking with detailed feedback
        • Direct integration with 4D analytic dimensions
        • Commitment lifecycle management
        • Consumption tracking interface

    Usage Example:
        class PurchaseOrder(models.Model):
            _inherit = ['purchase.order', 'budget.commitment.mixin']

            # Define field names for dynamic access
            _commitment_id_field = 'budget_commitment_id'
            _commitment_account_id_field = 'budget_account_id'

            budget_commitment_id = fields.Many2one('budget.commitment')
            budget_account_id = fields.Many2one('budget.account')

            def action_reserve_budget(self):
                commitment = self._create_budget_commitment(
                    amount=self.amount_total,
                    activity_analytic_id=self.project_activity_id,
                    fund_analytic_id=self.funding_source_id
                )
                return commitment

    Integration Points:
        • Purchase Orders: Reserve budget when PO is confirmed
        • Expense Claims: Reserve budget for employee expenses
        • Payment Requests: Reserve budget for pending payments
        • Project Tasks: Reserve budget for project activities
        • Any custom module requiring budget control
    """
    _name = 'budget.commitment.mixin'
    _description = 'Budget Commitment Mixin'

    # Configuration fields - override these in inheriting models
    _commitment_id_field = 'budget_commitment_id'  # Name of the field linking to budget.commitment
    _commitment_account_id_field = 'budget_account_id'  # Name of the field linking to budget.account

    def _get_commitment_field_value(self, field_name):
        """
        Get the value of a dynamic commitment field.

        Args:
            field_name (str): The name of the field to get ('commitment_id' or 'account_id')

        Returns:
            The field value or False if field doesn't exist or is empty
        """
        self.ensure_one()

        if field_name == 'commitment_id':
            actual_field_name = getattr(self.__class__, '_commitment_id_field', 'budget_commitment_id')
        elif field_name == 'account_id':
            actual_field_name = getattr(self.__class__, '_commitment_account_id_field', 'budget_account_id')
        else:
            raise ValueError(f"Unknown field_name: {field_name}")

        if hasattr(self, actual_field_name):
            return getattr(self, actual_field_name)
        return False

    def _set_commitment_field_value(self, field_name, value):
        """
        Set the value of a dynamic commitment field.

        Args:
            field_name (str): The name of the field to set ('commitment_id')
            value: The value to set
        """
        self.ensure_one()

        if field_name == 'commitment_id':
            actual_field_name = getattr(self.__class__, '_commitment_id_field', 'budget_commitment_id')
        else:
            raise ValueError(f"Unknown field_name: {field_name}")

        if hasattr(self, actual_field_name):
            setattr(self, actual_field_name, value)
        else:
            _logger.warning(f"Field {actual_field_name} not found on model {self._name}")

    def _create_budget_commitment(self, amount, activity_analytic_id, fund_analytic_id,
                                 department_analytic_id=None, source_analytic_id=None,
                                 ref=None, description=None, auto_reserve=True, **kwargs):
        """
        Create or reuse a budget commitment using the record's dynamic budget account field.

        If a cancelled commitment exists for this record, it will be reused by resetting
        it to draft and updating its values. Otherwise, a new commitment will be created.

        Args:
            amount (float): Amount to commit
            activity_analytic_id: Activity dimension (record or ID) - Required
            fund_analytic_id: Fund dimension (record or ID) - Required
            department_analytic_id: Department dimension (record or ID) - Optional
            source_analytic_id: Source dimension (record or ID) - Optional
            ref (str): Optional reference (defaults to record name if available)
            description (str): Optional description
            auto_reserve (bool): Automatically reserve the commitment
            **kwargs: Additional optional fields

        Returns:
            budget.commitment: Created or reused commitment record
        """
        self.ensure_one()

        # Get budget account from dynamic field
        budget_account_id = self._get_commitment_field_value('account_id')
        if not budget_account_id:
            raise ValidationError(_(
                "Budget account field '%s' is not set on this record"
            ) % getattr(self.__class__, '_commitment_account_id_field', 'budget_account_id'))

        # Check if there's an existing cancelled commitment to reuse
        existing_commitment = self._get_commitment_field_value('commitment_id')
        if existing_commitment and existing_commitment.state in ['cancel', 'draft']:
            commitment = self._reuse_cancelled_commitment(
                existing_commitment, amount, activity_analytic_id, fund_analytic_id,
                department_analytic_id, source_analytic_id, ref, description,
                budget_account_id, **kwargs
            )
        else:
            # No cancelled commitment exists, create a new one
            commitment = self._create_new_commitment(
                amount, activity_analytic_id, fund_analytic_id,
                department_analytic_id, source_analytic_id, ref, description,
                budget_account_id, **kwargs
            )

        # Auto reserve if requested
        if auto_reserve:
            try:
                commitment.action_reserve()
            except UserError as e:
                # If we were reusing, don't delete it, just keep it in draft
                if not (existing_commitment and existing_commitment == commitment):
                    commitment.unlink()
                raise UserError(_(
                    "Failed to reserve budget commitment: %s"
                ) % str(e))

        # Store commitment in dynamic field (in case it's a new one)
        self._set_commitment_field_value('commitment_id', commitment)

        return commitment

    def _prepare_commitment_vals(self, amount, activity_analytic_id, fund_analytic_id,
                                department_analytic_id, source_analytic_id, ref, description,
                                budget_account_id, include_company=True, **kwargs):
        """
        Prepare commitment values dictionary.

        Args:
            amount (float): Commitment amount
            activity_analytic_id: Activity dimension
            fund_analytic_id: Fund dimension
            department_analytic_id: Department dimension
            source_analytic_id: Source dimension
            ref (str): Reference
            description (str): Description
            budget_account_id: Budget account
            include_company (bool): Whether to include company_id
            **kwargs: Additional fields

        Returns:
            dict: Commitment values dictionary
        """
        commitment_vals = {
            'amount': amount,
            'account_id': budget_account_id.id if hasattr(budget_account_id, 'id') else budget_account_id,
            'activity_analytic_id': activity_analytic_id.id if hasattr(activity_analytic_id, 'id') else activity_analytic_id,
            'fund_analytic_id': fund_analytic_id.id if hasattr(fund_analytic_id, 'id') else fund_analytic_id,
            'department_analytic_id': department_analytic_id.id if hasattr(department_analytic_id, 'id') else department_analytic_id,
            'source_analytic_id': source_analytic_id.id if hasattr(source_analytic_id, 'id') else source_analytic_id,
            'ref': ref,
            'description': description or '',
            'user_id': self.env.user.id,
        }

        if include_company:
            commitment_vals['company_id'] = self.env.company.id

        # Handle date and fiscal year
        commitment_date = kwargs.get('date', fields.Date.today())
        commitment_vals['date'] = commitment_date

        if not kwargs.get('date_range_fy_id'):
            company_id = kwargs.get('company_id',
                                  self.company_id.id if hasattr(self, 'company_id') and self.company_id else self.env.company.id)
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

        return commitment_vals

    def _reuse_cancelled_commitment(self, existing_commitment, amount, activity_analytic_id, fund_analytic_id,
                                   department_analytic_id, source_analytic_id, ref, description,
                                   budget_account_id, **kwargs):
        """
        Reuse an existing cancelled commitment by resetting and updating it.

        Args:
            existing_commitment: The cancelled commitment to reuse
            amount (float): New commitment amount
            activity_analytic_id: Activity dimension
            fund_analytic_id: Fund dimension
            department_analytic_id: Department dimension
            source_analytic_id: Source dimension
            ref (str): Reference
            description (str): Description
            budget_account_id: Budget account
            **kwargs: Additional fields

        Returns:
            budget.commitment: Updated commitment
        """
        _logger.info(
            "Reusing cancelled budget commitment %s for %s",
            existing_commitment.name,
            self._name
        )

        # Reset the cancelled commitment to draft
        existing_commitment.action_reset_to_draft()

        # Prepare and apply update values
        commitment_vals = self._prepare_commitment_vals(
            amount, activity_analytic_id, fund_analytic_id,
            department_analytic_id, source_analytic_id, ref, description,
            budget_account_id, include_company=False, **kwargs
        )

        existing_commitment.write(commitment_vals)

        _logger.info(
            "Updated reused commitment %s with new values for %s amount %s",
            existing_commitment.name,
            self._name,
            existing_commitment.amount
        )

        return existing_commitment

    def _create_new_commitment(self, amount, activity_analytic_id, fund_analytic_id,
                              department_analytic_id, source_analytic_id, ref, description,
                              budget_account_id, **kwargs):
        """
        Create a new budget commitment.

        Args:
            amount (float): Commitment amount
            activity_analytic_id: Activity dimension
            fund_analytic_id: Fund dimension
            department_analytic_id: Department dimension
            source_analytic_id: Source dimension
            ref (str): Reference
            description (str): Description
            budget_account_id: Budget account
            **kwargs: Additional fields

        Returns:
            budget.commitment: New commitment
        """
        commitment_vals = self._prepare_commitment_vals(
            amount, activity_analytic_id, fund_analytic_id,
            department_analytic_id, source_analytic_id, ref, description,
            budget_account_id, include_company=True, **kwargs
        )

        commitment = self.env['budget.commitment'].create(commitment_vals)

        _logger.info(
            "Created new budget commitment %s for %s amount %s",
            commitment.name,
            self._name,
            commitment.amount
        )

        return commitment

    def _check_budget_availability(self, amount, activity_analytic_id, fund_analytic_id,
                                  department_analytic_id=None, source_analytic_id=None,
                                  **kwargs):
        """
        Check budget availability using the record's dynamic budget account field.

        Args:
            amount (float): Amount to check
            activity_analytic_id: Activity dimension (record or ID) - Required
            fund_analytic_id: Fund dimension (record or ID) - Required
            department_analytic_id: Department dimension (record or ID) - Optional
            source_analytic_id: Source dimension (record or ID) - Optional
            **kwargs: Optional overrides for date_range_fy_id, company_id

        Returns:
            dict: Budget availability information
        """
        self.ensure_one()

        # Get budget account from dynamic field
        budget_account_id = self._get_commitment_field_value('account_id')
        if not budget_account_id:
            raise ValidationError(_(
                "Budget account field '%s' is not set on this record"
            ) % getattr(self.__class__, '_commitment_account_id_field', 'budget_account_id'))

        account_id = budget_account_id.id if hasattr(budget_account_id, 'id') else budget_account_id

        # Get budget controller
        budget_controller = self.env['budget.controller']

        # Prepare analytic data
        analytic_data = {
            'account_id': account_id,
            'activity_analytic_id': activity_analytic_id.id if hasattr(activity_analytic_id, 'id') else activity_analytic_id,
            'fund_analytic_id': fund_analytic_id.id if hasattr(fund_analytic_id, 'id') else fund_analytic_id,
            'department_analytic_id': department_analytic_id.id if department_analytic_id and hasattr(department_analytic_id, 'id') else (department_analytic_id or False),
            'source_analytic_id': source_analytic_id.id if source_analytic_id and hasattr(source_analytic_id, 'id') else (source_analytic_id or False),
        }

        # Determine fiscal year
        if not kwargs.get('date_range_fy_id'):
            check_date = kwargs.get('date', fields.Date.today())
            company_id = kwargs.get('company_id',
                                  self.company_id.id if hasattr(self, 'company_id') and self.company_id else self.env.company.id)
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
                               self.company_id.id if hasattr(self, 'company_id') and self.company_id else self.env.company.id)

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

    def _cancel_budget_commitment(self, commitment=None):
        """
        Cancel a budget commitment and release the reserved budget.
        If no commitment is provided, uses the record's dynamic commitment field.

        Args:
            commitment (budget.commitment, optional): Commitment to cancel
                                                     If None, uses record's commitment field

        Returns:
            bool: True if successful

        Raises:
            UserError: If commitment cannot be cancelled
        """
        self.ensure_one()

        if commitment is None:
            commitment = self._get_commitment_field_value('commitment_id')

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

    def _obligate_budget_commitment(self, commitment=None):
        """
        Obligate a budget commitment (mark as obligated).
        This transitions from reserved to obligated state for firm commitments.
        If no commitment is provided, uses the record's dynamic commitment field.

        Args:
            commitment (budget.commitment, optional): Commitment to obligate
                                                     If None, uses record's commitment field

        Returns:
            bool: True if successful

        Raises:
            UserError: If commitment cannot be obligated
        """
        self.ensure_one()

        if commitment is None:
            commitment = self._get_commitment_field_value('commitment_id')

        if not commitment:
            return True

        if commitment.state == 'obligated':
            return True  # Already obligated

        if commitment.state != 'reserved':
            raise UserError(_(
                "Cannot obligate commitment %s - it must be in reserved state"
            ) % commitment.name)

        commitment.action_obligate()
        _logger.info("Obligated budget commitment %s", commitment.name)

        return True

    def _close_budget_commitment(self, commitment=None):
        """
        Close a budget commitment (mark as done).
        This releases any unused budget back to the pool.
        If no commitment is provided, uses the record's dynamic commitment field.

        Args:
            commitment (budget.commitment, optional): Commitment to close
                                                     If None, uses record's commitment field

        Returns:
            bool: True if successful

        Raises:
            UserError: If commitment cannot be closed
        """
        self.ensure_one()

        if commitment is None:
            commitment = self._get_commitment_field_value('commitment_id')

        if not commitment:
            return True

        if commitment.state == 'done':
            return True  # Already done

        if commitment.state != 'obligated':
            raise UserError(_(
                "Cannot close commitment %s - it must be in obligated state"
            ) % commitment.name)

        commitment.action_done()
        _logger.info(
            "Closed budget commitment %s - Released %.2f",
            commitment.name,
            commitment.remaining_amount
        )

        return True

    def _update_commitment_amount(self, new_amount, commitment=None):
        """
        Update commitment amount with validation.
        If no commitment is provided, uses the record's dynamic commitment field.

        Args:
            new_amount (float): New commitment amount
            commitment (budget.commitment, optional): Commitment to update
                                                     If None, uses record's commitment field

        Returns:
            bool: True if successful

        Raises:
            ValidationError: If new amount is invalid
            UserError: If budget is insufficient for increase
        """
        self.ensure_one()

        if commitment is None:
            commitment = self._get_commitment_field_value('commitment_id')

        if not commitment:
            raise ValidationError(_("No commitment to update"))

        if commitment.state not in ['reserved', 'obligated']:
            raise UserError(_(
                "Can only update amount for reserved or obligated commitments"
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

            # Create a temporary context with the commitment's analytics to check availability
            temp_self = self.env[self._name].new({
                getattr(self.__class__, '_commitment_account_id_field', 'budget_account_id'): commitment.account_id.id
            })

            # Check availability for the increase using commitment's analytics
            check_result = temp_self._check_budget_availability(
                amount=increase,
                activity_analytic_id=commitment.activity_analytic_id,
                fund_analytic_id=commitment.fund_analytic_id,
                department_analytic_id=commitment.department_analytic_id,
                source_analytic_id=commitment.source_analytic_id,
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

    def _consume_commitment(self, amount, reference=None, commitment=None):
        """
        Record consumption against a commitment.
        Creates a budget move to consume the committed amount.
        If no commitment is provided, uses the record's dynamic commitment field.

        Args:
            amount (float): Amount to consume
            reference (str, optional): Reference for the consumption
            commitment (budget.commitment, optional): Commitment to consume from
                                                     If None, uses record's commitment field

        Returns:
            budget.move: Created budget move for consumption

        Raises:
            ValidationError: If amount exceeds remaining commitment
        """
        self.ensure_one()

        if commitment is None:
            commitment = self._get_commitment_field_value('commitment_id')

        if not commitment:
            raise ValidationError(_("No commitment to consume"))

        if commitment.state not in ['reserved', 'obligated']:
            raise UserError(_(
                "Can only consume from reserved or obligated commitments"
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
