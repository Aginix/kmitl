import logging
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetController(models.AbstractModel):
    """
    Budget Controller - Centralized service for budget operations and availability checking.

    Architecture Purpose:
        The Budget Controller implements a service-oriented architecture pattern,
        providing a centralized, optimized, and consistent interface for all
        budget-related calculations across the KMITL budget system.

    Core Responsibilities:
        • **Budget Availability Checking**: Hierarchical calculation across 4D analytics
        • **Budget Calculation Service**: Optimized queries for appropriated/reserved/consumed amounts
        • **Budget Reservation Coordination**: Service-level budget commitment creation
        • **Budget Consumption Management**: Centralized consumption move creation
        • **Multi-line Bulk Operations**: Efficient batch processing for large datasets

    Service Architecture Benefits:
        • **Consistency**: Same calculation logic used across all modules
        • **Performance**: Optimized queries with strategic caching
        • **Maintainability**: Single source of truth for budget algorithms
        • **Extensibility**: Easy to add new budget operations
        • **Integration**: Clean API for external module integration

    Hierarchical Budget Algorithm:
        The controller implements sophisticated hierarchical budget matching:

        1. **Appropriation Matching** (Flexible):
           • Parent appropriations can cover child commitments
           • Uses parent_path traversal for efficient hierarchy checking
           • Supports complex Thai organizational structures

        2. **Commitment/Consumption Matching** (Exact):
           • Exact analytic matching for precise tracking
           • Prevents budget leakage between different allocations
           • Maintains strict audit trail

    4D Analytic Integration:
        • **Activities**: งานบริหาร > งานสำนักงาน > งานธุรการ (hierarchical)
        • **Departments**: สำนักงานอธิการบดี > งานบุคคล > งานสรรหา (hierarchical)
        • **Funds**: เงินรายได้ > เงินค่าบำรุง > เงินค่าสาธารณูปโภค (hierarchical)
        • **Sources**: เงินแผ่นดิน, เงินนอกงบประมาณ, เงินบริจาค (exact match)
        • **Budget Accounts**: 62010 - วัสดุสำนักงาน (exact match)

    Performance Optimizations:
        • **Strategic Queries**: Minimal database hits with optimized domains
        • **Bulk Operations**: Batch processing for multiple budget lines
        • **Caching Strategy**: Fiscal year and company-level query optimization
        • **Efficient Hierarchies**: parent_path traversal vs recursive queries
        • **Smart Filtering**: Early validation and data filtering

    Integration Patterns:
        **Direct Usage:**
        ```python
        budget_controller = self.env['budget.controller']
        available = budget_controller.get_available_budget(analytic_data, fy_id)
        ```

        **Via Budget Commitments:**
        ```python
        commitment._check_budget_availability()  # Uses controller internally
        ```

        **Via Budget Mixin:**
        ```python
        purchase_request._auto_create_budget_commitment()  # Uses controller
        ```

        **Bulk Operations:**
        ```python
        statuses = budget_controller.get_multi_line_budget_status(lines, fy_id)
        ```

    Error Handling Strategy:
        • **Graceful Degradation**: Continue operation with partial failures
        • **Detailed Error Messages**: User-friendly validation feedback
        • **Logging Integration**: Comprehensive audit trail
        • **Transaction Safety**: Atomic operations with rollback support

    Thai Localization Features:
        • **Government Standards**: Aligned with Thai government accounting
        • **Fiscal Year Support**: October-September Thai fiscal calendar
        • **Multi-level Hierarchies**: Supports complex Thai organizational charts
        • **Currency Handling**: Thai Baht primary with multi-currency support
        • **Compliance Reporting**: Government-required budget execution formats

    Usage Examples:
        **Check Single Budget Line:**
        ```python
        analytic_data = {
            'account_id': 12345,
            'activity_analytic_id': 100,
            'department_analytic_id': 200,
            'fund_analytic_id': 300,
            'source_analytic_id': 400
        }
        controller.check_budget_availability(analytic_data, 50000, fiscal_year.id)
        ```

        **Get Detailed Budget Status:**
        ```python
        status = controller.get_budget_status(analytic_data, fiscal_year.id)
        # Returns: appropriated, reserved, consumed, available, utilization %
        ```

        **Service-Level Reservation:**
        ```python
        commitment = controller.reserve_budget(analytic_data, 25000, fiscal_year.id, source_record)
        ```
    """
    _name = 'budget.controller'
    _description = 'Budget Controller Service'

    @api.model
    def check_budget_availability(self, analytic_data, amount, fiscal_year_id, company_id=None):
        """
        Check if sufficient budget is available for the given analytic combination

        Args:
            analytic_data (dict): Analytic dimensions data
                - account_id: Budget account ID
                - activity_analytic_id: Activity analytic account ID
                - department_analytic_id: Department analytic account ID
                - fund_analytic_id: Fund analytic account ID
                - source_analytic_id: Source analytic account ID
            amount (float): Amount to check availability for
            fiscal_year_id (int): Fiscal year ID
            company_id (int): Company ID (defaults to current company)

        Returns:
            bool: True if budget is available

        Raises:
            ValidationError: If insufficient budget is available
        """
        if not company_id:
            company_id = self.env.company.id

        available_amount = self.get_available_budget(analytic_data, fiscal_year_id, company_id)

        if amount > available_amount:
            error_msg = self._format_budget_shortage_message(analytic_data, available_amount, amount)
            raise ValidationError(error_msg)

        return True

    @api.model
    def get_available_budget(self, analytic_data, fiscal_year_id, company_id=None):
        """
        Get available budget amount for the given analytic combination

        Args:
            analytic_data (dict): Analytic dimensions data
            fiscal_year_id (int): Fiscal year ID
            company_id (int): Company ID (defaults to current company)

        Returns:
            float: Available budget amount
        """
        if not company_id:
            company_id = self.env.company.id

        # Calculate: Appropriated - Reserved - Consumed
        appropriated = self._calculate_appropriated_amount(analytic_data, fiscal_year_id, company_id)
        reserved = self._calculate_reserved_amount(analytic_data, fiscal_year_id, company_id)
        consumed = self._calculate_consumed_amount(analytic_data, fiscal_year_id, company_id)

        available = appropriated - reserved - consumed
        return max(0.0, available)  # Never return negative

    @api.model
    def reserve_budget(self, analytic_data, amount, fiscal_year_id, source_record=None, company_id=None):
        """
        Reserve budget amount by creating and reserving a commitment

        Args:
            analytic_data (dict): Analytic dimensions data
            amount (float): Amount to reserve
            fiscal_year_id (int): Fiscal year ID
            source_record (record): Source record requesting the reservation
            company_id (int): Company ID (defaults to current company)

        Returns:
            budget.commitment: Created and reserved commitment
        """
        if not company_id:
            company_id = self.env.company.id

        # Check availability first
        self.check_budget_availability(analytic_data, amount, fiscal_year_id, company_id)

        # Create commitment
        commitment_data = self._prepare_service_commitment_data(
            analytic_data, amount, fiscal_year_id, source_record, company_id
        )

        commitment = self.env['budget.commitment'].create(commitment_data)

        # Start (confirm + reserve)
        commitment.action_start()

        _logger.info('Reserved budget amount %s via service for %s',
                    amount, source_record._name if source_record else 'service')

        return commitment

    @api.model
    def get_budget_breakdown(self, analytic_data, fiscal_year_id=None, company_id=None):
        """
        Get detailed budget breakdown for the given analytic combination

        Args:
            analytic_data (dict): Analytic dimensions data
            fiscal_year_id (int): Fiscal year ID (optional)
            company_id (int): Company ID (defaults to current company)

        Returns:
            dict: Budget breakdown with appropriated, reserved, consumed, and available amounts
        """
        if not company_id:
            company_id = self.env.company.id

        if not fiscal_year_id:
            # Try to get current fiscal year
            today = fields.Date.today()
            fiscal_year = self.env['account.fiscal.year'].search([
                ('date_from', '<=', today),
                ('date_to', '>=', today),
                ('company_id', '=', company_id),
            ], limit=1)
            fiscal_year_id = fiscal_year.id if fiscal_year else False

        if not fiscal_year_id:
            return {
                'appropriated': 0.0,
                'reserved': 0.0,
                'consumed': 0.0,
                'available': 0.0,
                'details': [],
            }

        appropriated = self._calculate_appropriated_amount(analytic_data, fiscal_year_id, company_id)
        reserved = self._calculate_reserved_amount(analytic_data, fiscal_year_id, company_id)
        consumed = self._calculate_consumed_amount(analytic_data, fiscal_year_id, company_id)
        available = appropriated - reserved - consumed

        # Get recent transaction details (optional)
        details = self._get_budget_transaction_details(analytic_data, fiscal_year_id, company_id)

        return {
            'appropriated': appropriated,
            'reserved': reserved,
            'consumed': consumed,
            'available': max(0.0, available),
            'details': details[:10],  # Return only last 10 transactions
        }

    @api.model
    def _get_budget_transaction_details(self, analytic_data, fiscal_year_id, company_id):
        """Get recent budget transactions for the given analytic combination"""
        details = []

        # Get appropriation moves
        BudgetMove = self.env['budget.move']
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'appropriation'),
            ('account_fiscal_year_id', '=', fiscal_year_id),
            ('company_id', '=', company_id),
        ]

        moves = BudgetMove.search(domain, order='date desc', limit=50)
        for move in moves:
            for line in move.line_ids:
                if self._line_matches_analytic_data(line, analytic_data):
                    details.append({
                        'id': line.id,
                        'date': move.date,
                        'type': 'appropriation',
                        'reference': move.name,
                        'amount': abs(line.balance),
                    })

        # Get consumption moves
        domain[1] = ('move_type', '=', 'consume')
        moves = BudgetMove.search(domain, order='date desc', limit=50)
        for move in moves:
            for line in move.line_ids:
                if self._line_matches_analytic_data(line, analytic_data):
                    details.append({
                        'id': line.id,
                        'date': move.date,
                        'type': 'consumed',
                        'reference': move.name,
                        'amount': -abs(line.balance),
                    })

        # Get reserve and obligate commitment lines
        commitment_lines = self.env['budget.commitment.line'].search([
            ('line_type', 'in', ['reserve', 'obligate']),
            ('commitment_id.state', '=', 'in_progress'),
            ('account_fiscal_year_id', '=', fiscal_year_id),
            ('company_id', '=', company_id),
        ], order='commitment_id desc', limit=50)

        for line in commitment_lines:
            if self._commitment_line_matches_analytic_data(line, analytic_data):
                details.append({
                    'id': line.id,
                    'date': line.date or line.commitment_id.date,
                    'type': line.line_type,
                    'reference': line.commitment_id.name,
                    'amount': -line.amount,
                })

        # Sort by date descending
        details.sort(key=lambda x: x['date'], reverse=True)

        return details

    @api.model
    def consume_budget(self, commitment_id, amount=None, source_record=None):
        """
        Consume budget from an existing commitment

        Args:
            commitment_id (int): Budget commitment ID
            amount (float): Amount to consume (defaults to remaining amount)
            source_record (record): Source record requesting the consumption

        Returns:
            budget.move: Created consumption move
        """
        commitment = self.env['budget.commitment'].browse(commitment_id)

        if not commitment.exists():
            raise UserError(_('Budget commitment not found.'))

        if commitment.state != 'in_progress':
            raise UserError(_('Budget commitment must be in progress to consume.'))

        consume_lines = commitment.consume(amount)
        for line in consume_lines:
            line.post_line()
        consumption_move = consume_lines.mapped('budget_move_id')

        _logger.info('Consumed budget amount %s from commitment %s via service for %s',
                    consumption_move.total_amount, commitment.name,
                    source_record._name if source_record else 'service')

        return consumption_move

    @api.model
    def get_budget_status(self, analytic_data, fiscal_year_id, company_id=None):
        """
        Get comprehensive budget status for the given analytic combination

        Args:
            analytic_data (dict): Analytic dimensions data
            fiscal_year_id (int): Fiscal year ID
            company_id (int): Company ID (defaults to current company)

        Returns:
            dict: Budget status with all amounts and percentages
        """
        if not company_id:
            company_id = self.env.company.id

        appropriated = self._calculate_appropriated_amount(analytic_data, fiscal_year_id, company_id)
        reserved = self._calculate_reserved_amount(analytic_data, fiscal_year_id, company_id)
        consumed = self._calculate_consumed_amount(analytic_data, fiscal_year_id, company_id)
        available = max(0.0, appropriated - reserved - consumed)

        total_used = reserved + consumed
        utilization = (total_used / appropriated * 100) if appropriated > 0 else 0

        return {
            'appropriated_amount': appropriated,
            'reserved_amount': reserved,
            'consumed_amount': consumed,
            'available_amount': available,
            'total_used': total_used,
            'utilization_percentage': utilization,
            'is_over_budget': total_used > appropriated,
            'shortage_amount': max(0.0, total_used - appropriated),
        }

    @api.model
    def _calculate_appropriated_amount(self, analytic_data, fiscal_year_id, company_id):
        """Calculate total appropriated budget for the analytic combination"""
        domain = [
            ('state', '=', 'posted'),
            ('move_type', 'in', ('appropriation', 'entry')),
            ('account_fiscal_year_id', '=', fiscal_year_id),
            ('company_id', '=', company_id),
        ]

        moves = self.env['budget.move'].search(domain)
        total = 0.0

        for move in moves:
            for line in move.line_ids:
                if self._line_matches_analytic_data(line, analytic_data):
                    total += line.balance

        return total

    @api.model
    def _calculate_reserved_amount(self, analytic_data, fiscal_year_id, company_id):
        """Calculate total reserved amount from commitment reserve lines.

        Returns SUM(reserve.amount) - consumed for matching active commitments.
        Since consumed is calculated separately by _calculate_consumed_amount,
        the net deduction from available = reserved + consumed = total_reserve.
        """
        reserve_lines = self.env['budget.commitment.line'].search([
            ('line_type', '=', 'reserve'),
            ('commitment_id.state', '=', 'in_progress'),
            ('account_fiscal_year_id', '=', fiscal_year_id),
            ('company_id', '=', company_id),
        ])

        # Sum reserve amounts for matching lines
        total_reserve = 0.0
        commitment_ids = set()
        for line in reserve_lines:
            if self._commitment_line_matches_analytic_data(line, analytic_data):
                total_reserve += line.amount
                commitment_ids.add(line.commitment_id.id)

        # Subtract consumed from those commitments (to avoid double counting
        # with _calculate_consumed_amount)
        consumed = 0.0
        if commitment_ids:
            consume_moves = self.env['budget.move'].search([
                ('state', '=', 'posted'),
                ('move_type', '=', 'consume'),
                ('commitment_id', 'in', list(commitment_ids)),
            ])
            for move in consume_moves:
                for ml in move.line_ids:
                    if self._line_matches_analytic_data(ml, analytic_data):
                        consumed += abs(ml.balance)

        return max(0.0, total_reserve - consumed)

    @api.model
    def _calculate_consumed_amount(self, analytic_data, fiscal_year_id, company_id):
        """Calculate total consumed amount from budget moves"""
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'consume'),
            ('account_fiscal_year_id', '=', fiscal_year_id),
            ('company_id', '=', company_id),
        ]

        moves = self.env['budget.move'].search(domain)
        total = 0.0

        for move in moves:
            for line in move.line_ids:
                if self._line_matches_analytic_data(line, analytic_data):
                    total += abs(line.balance)

        return total

    @api.model
    def _commitment_line_matches_analytic_data(self, line, analytic_data):
        """Check if commitment line matches the given analytic data (hierarchical)"""
        return self._line_matches_analytic_data(line, analytic_data)

    @api.model
    def _line_matches_analytic_data(self, line, analytic_data):
        """Check if budget move line matches the given analytic data"""
        # Exact match for budget account and source
        if line.account_id.id != analytic_data.get('account_id'):
            return False
        if line.source_analytic_id.id != analytic_data.get('source_analytic_id', False):
            return False

        # Hierarchical match for other dimensions
        if not self._analytic_matches_hierarchical(
            line.activity_analytic_id.id if line.activity_analytic_id else False,
            analytic_data.get('activity_analytic_id', False)
        ):
            return False

        if not self._analytic_matches_hierarchical(
            line.department_analytic_id.id if line.department_analytic_id else False,
            analytic_data.get('department_analytic_id', False)
        ):
            return False

        if not self._analytic_matches_hierarchical(
            line.fund_analytic_id.id if line.fund_analytic_id else False,
            analytic_data.get('fund_analytic_id', False)
        ):
            return False

        return True

    def _analytic_matches_hierarchical(self, parent_id, child_id):
        """Check if analytic accounts match hierarchically"""
        # Handle None cases
        if not parent_id and not child_id:
            return True
        if not parent_id or not child_id:
            return False

        # Exact match
        if parent_id == child_id:
            return True

        # Check if parent_id is an ancestor of child_id
        child_account = self.env['account.analytic.account'].browse(child_id)
        if child_account.exists() and child_account.parent_path:
            parent_ids = [int(id_str) for id_str in child_account.parent_path.strip('/').split('/') if id_str.isdigit()]
            return parent_id in parent_ids

        return False

    def _format_budget_shortage_message(self, analytic_data, available_amount, requested_amount):
        """Format detailed budget shortage error message"""
        # Get record names for better error messages
        account = self.env['budget.account'].browse(analytic_data.get('account_id'))
        activity = self.env['account.analytic.account'].browse(analytic_data.get('activity_analytic_id'))
        department = self.env['account.analytic.account'].browse(analytic_data.get('department_analytic_id'))
        fund = self.env['account.analytic.account'].browse(analytic_data.get('fund_analytic_id'))
        source = self.env['account.analytic.account'].browse(analytic_data.get('source_analytic_id'))

        error_msg = _(
            "Insufficient budget available:\n"
            "- Budget Account: %(account)s\n"
            "- Activity: %(activity)s\n"
            "- Department: %(department)s\n"
            "- Fund: %(fund)s\n"
            "- Source: %(source)s\n"
            "- Available: %(available).2f\n"
            "- Requested: %(requested).2f\n"
            "- Shortage: %(shortage).2f"
        ) % {
            'account': account.display_name if account else 'N/A',
            'activity': activity.display_name if activity else 'N/A',
            'department': department.display_name if department else 'N/A',
            'fund': fund.display_name if fund else 'N/A',
            'source': source.display_name if source else 'N/A',
            'available': available_amount,
            'requested': requested_amount,
            'shortage': requested_amount - available_amount,
        }

        return error_msg

    @api.model
    def _prepare_service_commitment_data(self, analytic_data, amount, fiscal_year_id, source_record, company_id):
        """Prepare commitment data for service-created commitments"""
        commitment_name = _('Service Commitment')
        if source_record:
            commitment_name = _('Commitment for %s') % (
                getattr(source_record, 'name', None) or
                f"{source_record._description} #{source_record.id}"
            )

        line_data = {
            'account_id': analytic_data.get('account_id'),
            'activity_analytic_id': analytic_data.get('activity_analytic_id'),
            'fund_analytic_id': analytic_data.get('fund_analytic_id'),
            'amount': amount,
            'name': _('Service reservation for %s') % (source_record._name if source_record else 'system'),
        }

        return {
            'name': commitment_name,
            'date': fields.Date.today(),
            'department_analytic_id': analytic_data.get('department_analytic_id'),
            'source_analytic_id': analytic_data.get('source_analytic_id'),
            'account_fiscal_year_id': fiscal_year_id,
            'company_id': company_id,
            'currency_id': self.env.company.currency_id.id,
            'line_ids': [(0, 0, line_data)],
        }

    @api.model
    def get_multi_line_budget_status(self, line_data_list, fiscal_year_id, company_id=None):
        """
        Get budget status for multiple budget lines at once (optimized for bulk operations)

        Args:
            line_data_list (list): List of analytic data dicts
            fiscal_year_id (int): Fiscal year ID
            company_id (int): Company ID (defaults to current company)

        Returns:
            dict: Mapping of line keys to budget status
        """
        if not company_id:
            company_id = self.env.company.id

        # Group lines by analytic combination for efficient calculation
        grouped_lines = defaultdict(list)
        for idx, line_data in enumerate(line_data_list):
            key = self._get_analytic_key(line_data)
            grouped_lines[key].append((idx, line_data))

        results = {}

        # Calculate budget status for each unique combination
        for key, lines in grouped_lines.items():
            # Use the first line's analytic data for calculation
            analytic_data = lines[0][1]
            budget_status = self.get_budget_status(analytic_data, fiscal_year_id, company_id)

            # Apply status to all lines with this combination
            for idx, line_data in lines:
                results[idx] = budget_status.copy()

        return results

    @api.model
    def _get_analytic_key(self, analytic_data):
        """Get unique key for analytic combination"""
        return (
            analytic_data.get('account_id'),
            analytic_data.get('activity_analytic_id'),
            analytic_data.get('department_analytic_id'),
            analytic_data.get('fund_analytic_id'),
            analytic_data.get('source_analytic_id'),
        )
