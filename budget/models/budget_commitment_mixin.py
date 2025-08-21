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
        • Simple parameter-based API for maximum flexibility
        • Direct analytic dimension specification
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

            def action_reserve_budget(self):
                commitment = self._create_budget_commitment(
                    amount=self.amount_total,
                    budget_account_id=self.budget_account_id,
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

    # Optional field to link to commitment (implement in inheriting model if needed)
    # budget_commitment_id = fields.Many2one('budget.commitment', string='Budget Commitment')

    # Budget account field (implement in inheriting model)
    # budget_account_id = fields.Many2one('budget.account', string='Budget Account')

    @api.model
    def _create_budget_commitment(self, amount, budget_account_id,
                                 activity_analytic_id, fund_analytic_id,
                                 department_analytic_id=None, source_analytic_id=None,
                                 ref=None, description=None, auto_reserve=True, **kwargs):
        """
        Create a budget commitment with analytic fields passed as parameters.

        Args:
            amount (float): Amount to commit
            budget_account_id: Budget account (record or ID)
            activity_analytic_id: Activity dimension (record or ID) - Required
            fund_analytic_id: Fund dimension (record or ID) - Required
            department_analytic_id: Department dimension (record or ID) - Optional
            source_analytic_id: Source dimension (record or ID) - Optional
            ref (str): Optional reference
            description (str): Optional description
            auto_reserve (bool): Automatically reserve the commitment
            **kwargs: Additional optional fields

        Returns:
            budget.commitment: Created commitment record
        """
        # Prepare commitment values
        commitment_vals = {
            'amount': amount,
            'account_id': budget_account_id.id if hasattr(budget_account_id, 'id') else budget_account_id,
            'activity_analytic_id': activity_analytic_id.id if hasattr(activity_analytic_id, 'id') else activity_analytic_id,
            'fund_analytic_id': fund_analytic_id.id if hasattr(fund_analytic_id, 'id') else fund_analytic_id,
            'department_analytic_id': department_analytic_id.id if hasattr(department_analytic_id, 'id') else department_analytic_id,
            'source_analytic_id': source_analytic_id.id if hasattr(source_analytic_id, 'id') else source_analytic_id,
            'ref': ref,
            'description': description or ''
        }

        # Date and fiscal year
        commitment_date = kwargs.get('date', fields.Date.today())
        commitment_vals['date'] = commitment_date

        if not kwargs.get('date_range_fy_id'):
            company_id = kwargs.get('company_id', self.env.company.id)
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
        commitment_vals['user_id'] = kwargs.get('user_id', self.env.user.id)
        commitment_vals['company_id'] = kwargs.get('company_id', self.env.company.id)

        # Create commitment
        commitment = self.env['budget.commitment'].create(commitment_vals)

        # Auto reserve if requested
        if auto_reserve:
            try:
                commitment.action_reserve()
            except UserError as e:
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


    @api.model
    def _check_budget_availability(self, amount, budget_account_id,
                                  activity_analytic_id, fund_analytic_id,
                                  department_analytic_id=None, source_analytic_id=None,
                                  **kwargs):
        """
        Check budget availability with analytic fields passed as parameters.

        Args:
            amount (float): Amount to check
            budget_account_id: Budget account (record or ID)
            activity_analytic_id: Activity dimension (record or ID) - Required
            fund_analytic_id: Fund dimension (record or ID) - Required
            department_analytic_id: Department dimension (record or ID) - Optional
            source_analytic_id: Source dimension (record or ID) - Optional
            **kwargs: Optional overrides for date_range_fy_id, company_id

        Returns:
            dict: Budget availability information
        """
        if not budget_account_id:
            raise ValidationError(_("Budget account is required to check availability"))

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
            company_id = kwargs.get('company_id', self.env.company.id)
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

        company_id = kwargs.get('company_id', self.env.company.id)

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

            # Check availability for the increase using commitment's analytics
            check_result = self._check_budget_availability(
                amount=increase,
                budget_account_id=commitment.account_id,
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

    def _consume_commitment(self, commitment, amount, reference=None):
        """
        Record consumption against a commitment.
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
