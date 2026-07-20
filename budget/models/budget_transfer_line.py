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
    _inherit = ["analytic.mixin"]
    _order = "transfer_id, sequence, id"

    # Basic Fields
    transfer_id = fields.Many2one(
        comodel_name="budget.transfer",
        string="โอนงบประมาณ",
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
        default="from",
        help="Direction of this transfer line"
    )

    # Budget Account
    budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        help="Budget account for this transfer line"
    )

    # Amount
    amount = fields.Float(
        string="จำนวนเงิน",
        required=True,
        digits="Budget Precision",
        help="Transfer amount for this line"
    )

    # Analytic Distribution (JSON source of truth) is provided by analytic.mixin,
    # which also adds search support and a GIN index. The convenience fields below
    # sync with it via _compute_analytic_fields / _inverse_analytic_fields.

    # Analytic Display Fields (for easier UI handling)
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_fields",
        inverse="_inverse_analytic_fields",
        domain=[("root_plan_id.code", "=", "activities")],
        help="Activity analytic account"
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_fields",
        inverse="_inverse_analytic_fields",
        domain=[("root_plan_id.code", "=", "departments")],
        help="Department analytic account"
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_fields",
        inverse="_inverse_analytic_fields",
        domain=[("root_plan_id.code", "=", "funds")],
        help="Fund analytic account"
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_fields",
        inverse="_inverse_analytic_fields",
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
        string="งบประมาณคงเหลือ",
        compute="_compute_available_budget",
        help="Available budget for this account and analytics"
    )

    budget_sufficient = fields.Boolean(
        string="Budget Sufficient",
        compute="_compute_available_budget",
        help="True if available budget is sufficient for this transfer"
    )

    @api.depends("analytic_distribution", "transfer_id.department_analytic_id", "transfer_id.source_analytic_id", "transfer_direction")
    def _compute_analytic_fields(self):
        """
        Compute individual analytic fields with automatic inheritance from transfer level.

        Analytics Inheritance Logic:
        - FROM lines: Inherit both department_analytic_id and source_analytic_id from transfer
        - TO lines: Inherit only source_analytic_id from transfer (same funding source)
        - Both: Can be overridden by specific analytic_distribution JSON

        This ensures:
        1. Consistent department/source tracking at transfer level
        2. Flexibility for line-specific analytics (activity, fund)
        3. Proper double-entry with matching analytics where needed
        """
        for line in self:
            # Initialize all fields
            line.activity_analytic_id = False
            line.department_analytic_id = False
            line.fund_analytic_id = False
            line.source_analytic_id = False

            # First, inherit from transfer level based on direction
            if line.transfer_id:
                if line.transfer_direction == "from":
                    # FROM lines inherit both department and source
                    line.department_analytic_id = line.transfer_id.department_analytic_id
                    line.source_analytic_id = line.transfer_id.source_analytic_id
                elif line.transfer_direction == "to":
                    # TO lines inherit only source
                    line.source_analytic_id = line.transfer_id.source_analytic_id

            # Then override with any specific distribution
            if line.analytic_distribution:
                # Extract analytic account IDs from distribution
                # Distribution format: {analytic_account_id: percentage}
                distribution = line.analytic_distribution or {}

                # Get all analytic accounts in distribution
                analytic_ids = [int(aid) for aid in distribution.keys() if aid.isdigit()]
                analytics = self.env["account.analytic.account"].browse(analytic_ids)

                # Map to appropriate fields based on plan code (override inherited values)
                activity = analytics.filtered(lambda a: a.root_plan_id.code == "activities")[:1]
                if activity:
                    line.activity_analytic_id = activity

                department = analytics.filtered(lambda a: a.root_plan_id.code == "departments")[:1]
                if department:
                    line.department_analytic_id = department

                fund = analytics.filtered(lambda a: a.root_plan_id.code == "funds")[:1]
                if fund:
                    line.fund_analytic_id = fund

                source = analytics.filtered(lambda a: a.root_plan_id.code == "sources")[:1]
                if source:
                    line.source_analytic_id = source

    def _inverse_analytic_fields(self):
        """Sync the individual analytic fields back into analytic_distribution."""
        for line in self:
            accounts = (
                line.activity_analytic_id
                | line.department_analytic_id
                | line.fund_analytic_id
                | line.source_analytic_id
            )
            line.analytic_distribution = (
                {str(account.id): 100.0 for account in accounts} or False
            )

    @api.depends(
        "budget_account_id",
        "analytic_distribution",
        "amount",
        "transfer_direction",
        "transfer_id.account_fiscal_year_id"
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
                fiscal_year_id = line.transfer_id.account_fiscal_year_id.id if line.transfer_id.account_fiscal_year_id else False

                # Build analytic data for budget controller
                # Note: BudgetController.get_available_budget() expects analytic_data dict
                analytic_data = {}
                if line.activity_analytic_id:
                    analytic_data["activity_analytic_id"] = line.activity_analytic_id.id
                if line.department_analytic_id:
                    analytic_data["department_analytic_id"] = line.department_analytic_id.id
                if line.fund_analytic_id:
                    analytic_data["fund_analytic_id"] = line.fund_analytic_id.id
                if line.source_analytic_id:
                    analytic_data["source_analytic_id"] = line.source_analytic_id.id
                if line.budget_account_id:
                    analytic_data["account_id"] = line.budget_account_id.id

                available = budget_controller.get_available_budget(
                    analytic_data=analytic_data,
                    fiscal_year_id=fiscal_year_id,
                    company_id=line.company_id.id
                )

                line.available_budget = available
                line.budget_sufficient = available >= line.amount

            except Exception as e:
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
