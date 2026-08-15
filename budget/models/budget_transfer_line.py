from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BudgetTransferLine(models.Model):
    """
    Budget Transfer Line - Individual transfer line items.

    Each line represents either a source (from) or destination (to) for the
    budget transfer with a budget account and a full analytic combination.

    Dimensions (ADR-0009): a transfer line is driven by its full
    ``analytic_distribution`` — all five active dimensions, including
    ``kmitl_project`` / ``procurement_plan`` — and its availability is read from
    the unified control-node engine (``budget.controller.get_available``), not
    the legacy four-dimension wrapper. ``sources`` (แหล่งเงิน) is fixed by the
    transfer header (FROM and TO share one source); every other dimension is per
    line.
    """

    _name = "budget.transfer.line"
    _description = "Budget Transfer Line"
    _inherit = ["analytic.mixin"]
    _order = "transfer_id, sequence, id"

    # Plan code -> convenience field, mirroring budget.controller._DIM_COLUMNS.
    # Adding a controlled dimension to a transfer line = one entry here.
    _DIM_FIELDS = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
        "kmitl_project": "kmitl_project_analytic_id",
        "procurement_plan": "procurement_plan_analytic_id",
    }

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

    # Analytic Distribution (JSON source of truth — the engine reads this) is
    # provided by analytic.mixin, which also adds search support and a GIN index.
    # The convenience fields below round-trip with it via _compute_analytic_fields
    # and the per-dimension inverses.

    # Analytic convenience fields (round-trip with analytic_distribution)
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_fields",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        help="Activity analytic account"
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_fields",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        help="Department analytic account"
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_fields",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        help="Fund analytic account"
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_fields",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        help="Source analytic account (fixed by the transfer header)"
    )

    # 5th-dimension columns (ADR-0009): a transfer may move budget out of /
    # into a procurement-plan or project bucket. These round-trip with
    # analytic_distribution like the four above.
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="โครงการ/กิจกรรม",
        compute="_compute_analytic_fields",
        inverse="_inverse_kmitl_project_analytic",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        help="Project analytic account (the budget bucket this line draws from / into)"
    )

    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แผนจัดซื้อจัดจ้าง",
        compute="_compute_analytic_fields",
        inverse="_inverse_procurement_plan_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        help="Procurement-plan analytic account (the budget bucket this line draws from / into)"
    )

    # Account-type booleans — used for conditional dim visibility in tree views.
    # Both fields come from optional modules (kmitl_project, procurement_plan);
    # we guard against missing fields so budget can install standalone.
    account_is_project = fields.Boolean(
        string="Is Project Account",
        compute="_compute_account_type_flags",
        help="True when the budget account is a project/activity type"
    )

    account_is_procurement = fields.Boolean(
        string="Is Procurement Account",
        compute="_compute_account_type_flags",
        help="True when the budget account is a procurement-plan type"
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
        help="Available budget for this account and analytics (control-node engine)"
    )

    budget_sufficient = fields.Boolean(
        string="Budget Sufficient",
        compute="_compute_available_budget",
        help="True if available budget is sufficient for this transfer"
    )

    @api.depends("budget_account_id")
    def _compute_account_type_flags(self):
        has_project = "is_project" in self.env["budget.account"]._fields
        has_proc = "procurement_plan" in self.env["budget.account"]._fields
        for line in self:
            acc = line.budget_account_id
            line.account_is_project = bool(acc and has_project and acc.is_project)
            line.account_is_procurement = bool(
                acc and has_proc and acc.procurement_plan
            )

    @api.depends(
        "analytic_distribution",
        "transfer_id.source_analytic_id",
        "transfer_id.department_analytic_id",
        "transfer_direction",
    )
    def _compute_analytic_fields(self):
        """Derive the convenience dimension fields from analytic_distribution.

        Inheritance (ADR-0009 dimension policy):
        - ``sources`` is fixed by the transfer header — both FROM and TO share
          one source (cross-source transfers are forbidden). It is never taken
          from the line distribution.
        - ``departments`` defaults to the header but is overridable per line
          (cross-department transfers are allowed).
        - ``activities`` / ``funds`` / ``kmitl_project`` / ``procurement_plan``
          come purely from the line distribution.
        """
        for line in self:
            line.activity_analytic_id = False
            line.department_analytic_id = False
            line.fund_analytic_id = False
            line.kmitl_project_analytic_id = False
            line.procurement_plan_analytic_id = False

            # Source is always the header's (fixed for the whole transfer).
            line.source_analytic_id = line.transfer_id.source_analytic_id

            # Department defaults to the header, overridable below.
            line.department_analytic_id = line.transfer_id.department_analytic_id

            distribution = line.analytic_distribution or {}
            analytic_ids = [int(aid) for aid in distribution if str(aid).isdigit()]
            if not analytic_ids:
                continue
            accounts = self.env["account.analytic.account"].browse(analytic_ids)
            by_code = {
                "activities": "activity_analytic_id",
                "departments": "department_analytic_id",
                "funds": "fund_analytic_id",
                "kmitl_project": "kmitl_project_analytic_id",
                "procurement_plan": "procurement_plan_analytic_id",
            }
            for account in accounts:
                field_name = by_code.get(account.plan_id.code)
                if field_name:
                    line[field_name] = account.id

    def _update_analytic_distribution(self):
        """Rebuild analytic_distribution from the convenience fields.

        Always stamps the header source so the stored distribution carries the
        full controlled-dimension set the engine matches on.
        """
        self.ensure_one()
        distribution = {}
        accounts = [
            self.activity_analytic_id,
            self.department_analytic_id,
            self.fund_analytic_id,
            self.transfer_id.source_analytic_id,
            self.kmitl_project_analytic_id,
            self.procurement_plan_analytic_id,
        ]
        for account in accounts:
            if account:
                distribution[str(account.id)] = 100.0
        self.analytic_distribution = distribution if distribution else False

    def _inverse_activity_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_department_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_fund_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_source_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_kmitl_project_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_procurement_plan_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    @api.depends(
        "budget_account_id",
        "analytic_distribution",
        "amount",
        "transfer_direction",
        "transfer_id.account_fiscal_year_id",
    )
    def _compute_available_budget(self):
        """Available budget for FROM lines via the control-node engine (ADR-0005).

        Reads the line's full ``analytic_distribution`` (all active dimensions),
        so a line drawing from a ``procurement_plan`` / ``kmitl_project`` bucket
        is evaluated against that exact bucket. The engine is no longer floored
        at zero, so ``available`` may be negative (over-committed); anything
        below the line amount is insufficient.
        """
        controller = self.env["budget.controller"]
        for line in self:
            if line.transfer_direction != "from" or not line.budget_account_id:
                line.available_budget = 0.0
                line.budget_sufficient = True
                continue

            fiscal_year = line.transfer_id.account_fiscal_year_id
            if not fiscal_year:
                line.available_budget = 0.0
                line.budget_sufficient = False
                continue

            available = controller.get_available(
                line.budget_account_id,
                line.analytic_distribution or {},
                fiscal_year.id,
                line.company_id.id or line.transfer_id.company_id.id,
            )
            line.available_budget = available
            line.budget_sufficient = available >= line.amount

    @api.constrains("amount")
    def _check_amount_positive(self):
        """Ensure amount is positive"""
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_("Transfer amount must be greater than zero"))

    @api.constrains("analytic_distribution")
    def _check_supplementary_dims_exclusive(self):
        """The two supplementary dimensions — โครงการ/กิจกรรม (kmitl_project) and
        แผนจัดซื้อจัดจ้าง (procurement_plan) — are mutually exclusive: a line may
        carry at most one of them, never both."""
        for line in self:
            if line.procurement_plan_analytic_id and line.kmitl_project_analytic_id:
                raise ValidationError(_(
                    "แต่ละบรรทัดเลือกได้เพียงมิติเดียวจาก โครงการ/กิจกรรม หรือ "
                    "แผนจัดซื้อจัดจ้าง — เลือกพร้อมกันไม่ได้"
                ))

    @api.constrains("analytic_distribution", "budget_account_id")
    def _check_supplementary_dims_match_account(self):
        """A project tag may only be set on a project-type account (is_project),
        and a procurement tag only on a procurement-type account."""
        has_proc = "procurement_plan" in self.env["budget.account"]._fields
        for line in self:
            acc = line.budget_account_id
            if not acc:
                continue
            if line.kmitl_project_analytic_id and not (
                "is_project" in acc._fields and acc.is_project
            ):
                raise ValidationError(_(
                    "มิติโครงการ/กิจกรรม ใส่ได้เฉพาะรหัสงบประมาณประเภทโครงการ "
                    "(is_project) เท่านั้น"
                ))
            if line.procurement_plan_analytic_id and not (
                has_proc and acc.procurement_plan
            ):
                raise ValidationError(_(
                    "มิติแผนจัดซื้อจัดจ้าง ใส่ได้เฉพาะรหัสงบประมาณ "
                    "ประเภทแผนจัดซื้อจัดจ้าง เท่านั้น"
                ))

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
