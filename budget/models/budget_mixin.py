import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetMixin(models.AbstractModel):
    """
    Budget Mixin - Integration framework for external modules with budget system.

    Business Purpose:
        Provides a standardized, reusable integration pattern for any Odoo module
        that needs to create budget commitments, track budget consumption, and
        maintain budget control throughout their business processes.

    Integration Architecture:
        The mixin implements a complete lifecycle integration pattern:

        **Standard Lifecycle Integration:**
        1. **Creation**: External record created → Optional budget commitment
        2. **Confirmation**: External record confirmed → Create/reserve budget commitment
        3. **Processing**: External record processed → Consume budget via moves
        4. **Cancellation**: External record cancelled → Cancel budget integration

        **Flexible Integration Patterns:**
        • **Automatic Integration**: _auto_* methods for seamless lifecycle hooks
        • **Manual Integration**: Direct method calls for custom workflows
        • **Selective Integration**: has_budget_integration flag for optional control
        • **Service Integration**: Uses budget.controller for optimized operations

    Integration Examples:
        **Purchase Request Integration:**
        ```python
        class PurchaseRequest(models.Model):
            _name = 'purchase.request'
            _inherit = ['purchase.request', 'budget.mixin']

            def action_confirm(self):
                result = super().action_confirm()
                if self.has_budget_integration:
                    self._auto_create_budget_commitment()
                    self._auto_reserve_budget_commitment()
                return result

            def _prepare_default_budget_lines(self):
                return [{
                    'account_id': self.budget_account_id.id,
                    'activity_analytic_id': self.activity_id.id,
                    'fund_analytic_id': self.fund_id.id,
                    'amount': self.estimated_cost,
                    'name': f'Purchase request: {self.name}'
                }]
        ```

        **Expense Claim Integration:**
        ```python
        class HrExpense(models.Model):
            _name = 'hr.expense'
            _inherit = ['hr.expense', 'budget.mixin']

            def action_submit_expenses(self):
                result = super().action_submit_expenses()
                self._auto_create_budget_commitment()
                return result

            def action_approve_expense_sheets(self):
                result = super().action_approve_expense_sheets()
                self._auto_consume_budget_commitment()
                return result
        ```

        **Asset Purchase Integration:**
        ```python
        class AccountAsset(models.Model):
            _name = 'account.asset'
            _inherit = ['account.asset', 'budget.mixin']

            def validate(self):
                result = super().validate()
                if self.has_budget_integration:
                    commitment = self.create_budget_commitment()
                    commitment.action_confirm()
                    commitment.action_reserve()
                    self.consume_budget_commitment()
                return result
        ```

    Required Method Overrides:
        External modules must implement these methods for proper integration:

        **_prepare_default_budget_lines()** - REQUIRED
        Define the budget line structure for commitments:
        ```python
        def _prepare_default_budget_lines(self):
            return [{
                'account_id': # Budget account ID
                'activity_analytic_id': # Activity analytic ID
                'fund_analytic_id': # Fund analytic ID
                'amount': # Commitment amount
                'name': # Line description
            }]
        ```

        **_get_department_analytic_id()** - REQUIRED
        Map to organizational department:
        ```python
        def _get_department_analytic_id(self):
            return self.department_id.analytic_account_id.id
        ```

        **_get_source_analytic_id()** - REQUIRED
        Map to funding source:
        ```python
        def _get_source_analytic_id(self):
            return self.funding_source_id.analytic_account_id.id
        ```

    Budget Integration Fields:
        • **budget_commitment_id**: Link to created budget commitment
        • **budget_move_id**: Link to consumption move (when consumed)
        • **budget_amount**: Total budget amount (computed from commitment)
        • **budget_state**: Current integration status
        • **has_budget_integration**: Toggle for optional budget control

    Lifecycle Hook Methods:
        **Automatic Integration Hooks:**
        • **_auto_create_budget_commitment()**: Create commitment automatically
        • **_auto_reserve_budget_commitment()**: Reserve budget automatically
        • **_auto_consume_budget_commitment()**: Consume budget automatically

        **Manual Integration Methods:**
        • **create_budget_commitment()**: Create commitment with validation
        • **reserve_budget_commitment()**: Reserve with availability checking
        • **consume_budget_commitment()**: Create consumption moves
        • **cancel_budget_integration()**: Handle cancellation cleanup

    Error Handling & Validation:
        • **Budget Availability**: Automatic checking before reservation
        • **Data Validation**: Required field validation with helpful messages
        • **State Management**: Proper state transitions and constraints
        • **Transaction Safety**: Atomic operations with rollback support

    Performance Features:
        • **Lazy Loading**: Budget calculations only when needed
        • **Bulk Operations**: Efficient handling of multiple records
        • **Smart Dependencies**: Optimized computed field triggers
        • **Controller Integration**: Leverages optimized budget service

    Thai Localization Support:
        • **Multi-level Analytics**: Supports complex Thai organizational hierarchies
        • **Government Standards**: Aligned with Thai accounting requirements
        • **Fiscal Year Integration**: Thai fiscal calendar support
        • **Multi-currency**: Thai Baht and foreign currency handling

    Integration Best Practices:
        1. **Optional Control**: Use has_budget_integration for flexible adoption
        2. **Proper Mapping**: Implement required override methods correctly
        3. **State Alignment**: Align budget states with business process states
        4. **Error Handling**: Provide user-friendly error messages
        5. **Testing**: Test budget integration scenarios thoroughly
        6. **Documentation**: Document integration patterns for maintainers
    """
    _name = 'budget.mixin'
    _description = 'Budget Integration Mixin'

    # Budget Integration Fields
    budget_commitment_id = fields.Many2one(
        comodel_name='budget.commitment',
        string='Budget Commitment',
        help='Budget commitment linked to this record',
        index=True,
        ondelete='set null',
        readonly=True,
    )

    budget_move_id = fields.Many2one(
        comodel_name='budget.move',
        string='Budget Move',
        help='Budget consumption move linked to this record',
        index=True,
        ondelete='set null',
        readonly=True,
    )

    budget_amount = fields.Monetary(
        string='Budget Amount',
        help='Total budget amount for this record',
        currency_field='currency_id',
        compute='_compute_budget_amount',
        store=True,
    )

    budget_state = fields.Selection(
        selection=[
            ('none', 'No Budget'),
            ('committed', 'Budget Committed'),
            ('reserved', 'Budget Reserved'),
            ('consumed', 'Budget Consumed'),
            ('cancelled', 'Budget Cancelled'),
        ],
        string='Budget Status',
        default='none',
        compute='_compute_budget_state',
        store=True,
        help='Current status of budget integration',
    )

    has_budget_integration = fields.Boolean(
        string='Has Budget Integration',
        default=False,
        help='Whether this record has budget integration enabled',
    )

    # Required fields that inheriting models should have
    # These will be used for budget commitment creation
    company_id = fields.Many2one('res.company', required=True)
    currency_id = fields.Many2one('res.currency', required=True)
    date = fields.Date(required=True)

    @api.depends('budget_commitment_id', 'budget_commitment_id.state', 'budget_move_id')
    def _compute_budget_state(self):
        """Compute budget state based on linked records"""
        for record in self:
            if record.budget_move_id:
                record.budget_state = 'consumed'
            elif record.budget_commitment_id:
                state = record.budget_commitment_id.state
                if state == 'reserved':
                    record.budget_state = 'reserved'
                elif state in ('partial', 'done'):
                    record.budget_state = 'consumed'
                elif state == 'cancel':
                    record.budget_state = 'cancelled'
                else:
                    record.budget_state = 'committed'
            else:
                record.budget_state = 'none'

    @api.depends('budget_commitment_id.amount')
    def _compute_budget_amount(self):
        """Compute budget amount from commitment cap"""
        for record in self:
            if record.budget_commitment_id:
                record.budget_amount = record.budget_commitment_id.amount
            else:
                record.budget_amount = 0.0

    def create_budget_commitment(self, line_data=None):
        """Create budget commitment with reserve lines.

        Args:
            line_data (list): List of dicts with budget line data.
                Each dict should contain: account_id, activity_analytic_id,
                fund_analytic_id, amount, name.

        Returns:
            budget.commitment: Created commitment record
        """
        self.ensure_one()

        if self.budget_commitment_id:
            raise UserError(_('Budget commitment already exists for this record.'))

        if not line_data:
            line_data = self._prepare_default_budget_lines()

        # Ensure lines have move_type and analytic_distribution
        processed_lines = []
        for line in line_data:
            line_vals = dict(line)
            line_vals.setdefault('move_type', 'reserve')
            # Build analytic_distribution from individual IDs if not present
            if not line_vals.get('analytic_distribution'):
                dist = {}
                if line_vals.get('activity_analytic_id'):
                    dist[str(line_vals['activity_analytic_id'])] = 100.0
                if line_vals.get('fund_analytic_id'):
                    dist[str(line_vals['fund_analytic_id'])] = 100.0
                line_vals['analytic_distribution'] = dist or False
            processed_lines.append(line_vals)

        commitment_data = self._prepare_budget_commitment_data()
        # Set cap amount as sum of line amounts
        total = sum(l.get('amount', 0) for l in processed_lines)
        commitment_data['amount'] = total
        commitment_data['line_ids'] = [(0, 0, line) for line in processed_lines]

        commitment = self.env['budget.commitment'].create(commitment_data)
        self.budget_commitment_id = commitment.id

        _logger.info('Created budget commitment %s for %s %s',
                    commitment.name, self._name, self.id)

        return commitment

    def consume_budget_commitment(self, amount=None):
        """
        Consume budget from the linked commitment

        Args:
            amount (float): Amount to consume. If None, consumes remaining amount.

        Returns:
            budget.move: Created consumption move
        """
        self.ensure_one()

        if not self.budget_commitment_id:
            raise UserError(_('No budget commitment found to consume from.'))

        if self.budget_commitment_id.state not in ('reserved', 'partial'):
            raise UserError(_('Budget commitment must be in reserved or partial state to consume.'))

        # Add a consume line to the commitment
        first_reserve = self.budget_commitment_id.line_ids.filtered(
            lambda l: l.move_type == 'reserve' and l.state == 'posted'
        )[:1]
        if not first_reserve:
            raise UserError(_('No active reserve lines found on commitment.'))

        consume_amount = amount if amount else self.budget_commitment_id.available_to_consume
        consume_line = self.env['budget.commitment.line'].create({
            'commitment_id': self.budget_commitment_id.id,
            'move_type': 'consume',
            'account_id': first_reserve.account_id.id,
            'analytic_distribution': first_reserve.analytic_distribution,
            'amount': consume_amount,
            'name': _('Consumption from %s') % self.display_name,
        })

        _logger.info('Consumed budget %s from commitment %s for %s %s',
                    consume_amount, self.budget_commitment_id.name,
                    self._name, self.id)

        return consume_line

    def cancel_budget_integration(self):
        """Cancel budget integration - sets commitment to cancelled state"""
        self.ensure_one()

        if self.budget_commitment_id and self.budget_commitment_id.state not in ['cancel', 'done']:
            self.budget_commitment_id.action_cancel()
            self.budget_commitment_id.message_post(
                body=_('Cancelled due to source record cancellation.')
            )

        _logger.info('Cancelled budget integration for %s %s', self._name, self.id)

    def reserve_budget_commitment(self):
        """Reserve the budget commitment"""
        self.ensure_one()

        if not self.budget_commitment_id:
            raise UserError(_('No budget commitment to reserve.'))

        if self.budget_commitment_id.state == 'draft':
            self.budget_commitment_id.action_reserve()

        return self.budget_commitment_id

    def _prepare_budget_commitment_data(self):
        """Prepare data for budget commitment creation."""
        dept_id = self._get_department_analytic_id()
        source_id = self._get_source_analytic_id()

        # Build header analytic_distribution (department + source)
        header_dist = {}
        if dept_id:
            header_dist[str(dept_id)] = 100.0
        if source_id:
            header_dist[str(source_id)] = 100.0

        return {
            'name': self._get_budget_commitment_name(),
            'date': self.date,
            'analytic_distribution': header_dist or False,
            'account_fiscal_year_id': self._get_fiscal_year_id(),
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'is_auto_created': True,
        }

    def _prepare_default_budget_lines(self):
        """
        Prepare default budget lines.
        Override this method in inheriting models.

        Returns:
            list: List of budget line data dicts
        """
        # This should be overridden by inheriting models
        raise NotImplementedError(
            _('Inheriting models must implement _prepare_default_budget_lines()')
        )

    def _get_budget_commitment_name(self):
        """Get name for budget commitment"""
        if hasattr(self, 'name') and self.name:
            return _('Commitment for %s') % self.name
        else:
            return _('Commitment for %s #%s') % (self._description, self.id)

    def _get_department_analytic_id(self):
        """
        Get department analytic account ID.
        Override this method in inheriting models.
        """
        # This should be overridden by inheriting models to return appropriate department
        return False

    def _get_source_analytic_id(self):
        """
        Get source analytic account ID.
        Override this method in inheriting models.
        """
        # This should be overridden by inheriting models to return appropriate source
        return False

    def _get_fiscal_year_id(self):
        """Get fiscal year for the commitment date"""
        fiscal_year = self.env['account.fiscal.year'].search([
            ('date_from', '<=', self.date),
            ('date_to', '>=', self.date),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if not fiscal_year:
            raise UserError(
                _('No fiscal year found for date %s. Please create the fiscal year first.') % self.date
            )

        return fiscal_year.id

    # Lifecycle hooks for automatic budget integration

    def _auto_create_budget_commitment(self):
        """Automatically create budget commitment."""
        if self.has_budget_integration and not self.budget_commitment_id:
            return self.create_budget_commitment()
        return False

    def _auto_reserve_budget_commitment(self):
        """Automatically reserve budget commitment."""
        if self.budget_commitment_id and self.budget_commitment_id.state == 'draft':
            self.budget_commitment_id.action_reserve()
            return True
        return False

    def _auto_consume_budget_commitment(self):
        """Automatically consume budget commitment."""
        if self.budget_commitment_id and self.budget_commitment_id.state in ('reserved', 'partial'):
            return self.consume_budget_commitment()
        return False

    def action_view_budget_commitment(self):
        """View the linked budget commitment"""
        self.ensure_one()

        if not self.budget_commitment_id:
            raise UserError(_('No budget commitment found for this record.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Commitment'),
            'res_model': 'budget.commitment',
            'res_id': self.budget_commitment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_budget_move(self):
        """View the linked budget move"""
        self.ensure_one()

        if not self.budget_move_id:
            raise UserError(_('No budget move found for this record.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Move'),
            'res_model': 'budget.move',
            'res_id': self.budget_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
