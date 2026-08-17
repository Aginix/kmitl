from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Columns that describe a transfer line's dimensions. A write touching any of
# them re-syncs analytic_distribution (below); analytic_distribution itself is
# deliberately excluded so the re-sync's own JSON write does not re-enter.
_DIM_TRIGGER = frozenset(
    {
        "account_id",
        "activity_analytic_id",
        "fund_analytic_id",
        "department_analytic_id",
        "source_analytic_id",
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
        "transfer_direction",
    }
)


class BudgetMoveLine(models.Model):
    """Transfer-authoring extension of the core budget move line (ADR-0013).

    When ``budget.transfer.line`` was folded into ``budget.move.line`` the line
    became the single authoring surface for a transfer. Everything a transfer
    needs that a plain ledger line does not — a FROM/TO ``direction``, a positive
    ``amount`` helper mapping to debit/credit, per-line availability, and the
    Pool-Tag rules (ADR-0009/0012) — lives here, in the feature module, so the
    core line file stays lean. All of it is scoped to *transfer lines*
    (``transfer_direction`` set); appropriation / consume lines are untouched.

    Dimensions: the four core dims live in their own columns (the engine matches
    columns, ``budget.controller._DIM_COLUMNS``); ``source`` is the move header's
    (``related``). The KMITL ``analytic.distribution.mixin`` rebuilds the JSON
    from those four columns on every edit — which would silently drop a Pool Tag
    (``kmitl_project`` / ``procurement_plan``), whose column is itself derived
    from the JSON. So the JSON is re-synced from all dimensions in create/write,
    pre-capturing the tags before the mixin's rebuild can wipe them.
    """

    _inherit = "budget.move.line"

    transfer_direction = fields.Selection(
        selection=[
            ("from", "Transfer Out (Source)"),
            ("to", "Transfer In (Destination)"),
        ],
        string="Direction",
        help="Set on a line that belongs to a budget transfer: FROM credits its "
        "bucket, TO debits its bucket.",
    )
    amount = fields.Float(
        string="Amount",
        digits="Budget Precision",
        help="Positive transfer amount; mapped to credit (FROM) or debit (TO).",
    )
    available_budget = fields.Float(
        string="Available Budget",
        compute="_compute_transfer_availability",
        help="Available budget at this line's dimensions (control-node engine).",
    )
    budget_sufficient = fields.Boolean(
        string="Budget Sufficient",
        compute="_compute_transfer_availability",
    )
    account_is_project = fields.Boolean(
        compute="_compute_account_type_flags",
        help="True when the budget account is a project/activity type.",
    )
    account_is_procurement = fields.Boolean(
        compute="_compute_account_type_flags",
        help="True when the budget account is a procurement-plan type.",
    )

    # The two Pool Tags are read-only mirrors of analytic_distribution upstream;
    # a transfer authors them, so make them writable. Their compute-from-JSON
    # stays (round-trip); the create/write sync keeps the JSON carrying them.
    kmitl_project_analytic_id = fields.Many2one(readonly=False)
    procurement_plan_analytic_id = fields.Many2one(readonly=False)

    # Source is the move header's, mirrored read-only onto the line.
    # Keep it read-only: as a *writable* related field a fresh line's empty
    # source would be pushed back onto the header and clear it (ADR-0009 — source
    # is locked to the header).
    source_analytic_id = fields.Many2one(readonly=True)

    def _analytic_keys(self):
        # Keep `source` out of the analytic round-trip: it is header-owned
        # (related, read-only above), so the mixin inverse must never write it
        # back from the line's analytic_distribution.
        keys = dict(super()._analytic_keys())
        keys.pop("sources", None)
        return keys

    # ------------------------------------------------------------------
    # analytic_distribution round-trip (tag-safe)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line, vals in zip(lines, vals_list):
            if not line.transfer_direction:
                continue
            tags = [
                vals.get("kmitl_project_analytic_id"),
                vals.get("procurement_plan_analytic_id"),
            ]
            # Not passed as columns → they may have arrived inside a supplied
            # analytic_distribution and already sit on the (computed) columns.
            line._sync_transfer_distribution(tags if any(tags) else None)
        return lines

    def write(self, vals):
        if self.env.context.get("_bt_syncing") or not (_DIM_TRIGGER & set(vals)):
            return super().write(vals)
        targets = self.filtered("transfer_direction")
        # Capture the tags before super()'s core-dim rebuild can drop them.
        pre_tags = {
            line.id: [
                line.kmitl_project_analytic_id.id,
                line.procurement_plan_analytic_id.id,
            ]
            for line in targets
        }
        res = super().write(vals)
        for line in targets:
            tags = [
                vals.get("kmitl_project_analytic_id", pre_tags[line.id][0]),
                vals.get("procurement_plan_analytic_id", pre_tags[line.id][1]),
            ]
            line._sync_transfer_distribution(tags)
        return res

    def _sync_transfer_distribution(self, tags=None):
        """Rebuild analytic_distribution from every dimension, keeping the tags.

        ``tags`` (a pair of ids/False) overrides the tag columns, which the
        mixin's core-dim rebuild may just have cleared. Idempotent: only writes
        when the JSON actually changes, so the inverse it triggers (which rewrites
        the core-dim columns) converges instead of looping.
        """
        self.ensure_one()
        distribution = {}
        # NB: source is deliberately excluded — it is header-owned and read-only
        # on the line (see _analytic_keys); writing it into the JSON would make
        # the inverse push it back onto the header. The availability query
        # (_transfer_distribution) still includes it from the column.
        for account in (
            self.activity_analytic_id,
            self.department_analytic_id,
            self.fund_analytic_id,
        ):
            if account:
                distribution[str(account.id)] = 100.0
        if tags is None:
            tags = [
                self.kmitl_project_analytic_id.id,
                self.procurement_plan_analytic_id.id,
            ]
        for tag_id in tags:
            if tag_id:
                distribution[str(tag_id)] = 100.0
        distribution = distribution or False
        if (self.analytic_distribution or False) != distribution:
            self.with_context(_bt_syncing=True).write(
                {"analytic_distribution": distribution}
            )

    def _transfer_distribution(self):
        """{analytic_id: 100} across every present dimension, for the
        availability query — read from the columns so it holds even mid-edit."""
        self.ensure_one()
        distribution = {}
        for account in (
            self.activity_analytic_id,
            self.department_analytic_id,
            self.fund_analytic_id,
            self.source_analytic_id,
            self.kmitl_project_analytic_id,
            self.procurement_plan_analytic_id,
        ):
            if account:
                distribution[str(account.id)] = 100.0
        return distribution

    # ------------------------------------------------------------------
    # Direction ↔ debit/credit/balance
    # ------------------------------------------------------------------
    def _apply_direction_amount(self):
        """Map the positive ``amount`` onto debit/credit/balance by direction.

        FROM (source) credits its bucket → negative balance; TO (destination)
        debits its bucket → positive balance. Idempotent.
        """
        for line in self:
            amount = line.amount or 0.0
            if line.transfer_direction == "to":
                debit, credit, balance = amount, 0.0, amount
            elif line.transfer_direction == "from":
                debit, credit, balance = 0.0, amount, -amount
            else:
                continue
            if (line.debit, line.credit, line.balance) != (debit, credit, balance):
                line.debit = debit
                line.credit = credit
                line.balance = balance

    @api.onchange(
        "amount",
        "transfer_direction",
        "account_id",
        "activity_analytic_id",
        "fund_analytic_id",
        "department_analytic_id",
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
    )
    def _onchange_transfer_line(self):
        """Keep debit/credit/balance and the JSON in step in the form."""
        for line in self.filtered("transfer_direction"):
            line._apply_direction_amount()
            line._sync_transfer_distribution()

    # ------------------------------------------------------------------
    # Availability + flags
    # ------------------------------------------------------------------
    @api.depends(
        "transfer_direction",
        "account_id",
        "amount",
        "activity_analytic_id",
        "fund_analytic_id",
        "department_analytic_id",
        "source_analytic_id",
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
        "move_id.move_type",
        "move_id.account_fiscal_year_id",
    )
    def _compute_transfer_availability(self):
        """FROM-line availability via the control-node engine (ADR-0009).

        Only meaningful for a *drawing* line — a FROM line of a non-appropriation
        move. The query distribution is built from the columns so it is correct
        regardless of the JSON round-trip state.
        """
        controller = self.env["budget.controller"]
        for line in self:
            move = line.move_id
            drawing = (
                line.transfer_direction == "from"
                and move.move_type != "appropriation"
                and line.account_id
            )
            if not drawing or not move.account_fiscal_year_id:
                line.available_budget = 0.0
                line.budget_sufficient = not drawing
                continue
            available = controller.get_available(
                line.account_id,
                line._transfer_distribution(),
                move.account_fiscal_year_id.id,
                line.company_id.id or move.company_id.id,
            )
            line.available_budget = available
            line.budget_sufficient = available >= (line.amount or 0.0)

    @api.depends("account_id")
    def _compute_account_type_flags(self):
        account_model = self.env["budget.account"]
        has_project = "is_project" in account_model._fields
        has_proc = "procurement_plan" in account_model._fields
        for line in self:
            account = line.account_id
            line.account_is_project = bool(
                account and has_project and account.is_project
            )
            line.account_is_procurement = bool(
                account and has_proc and account.procurement_plan
            )

    # ------------------------------------------------------------------
    # Transfer-line constraints (ADR-0009 / ADR-0012) — scoped to transfer lines
    # ------------------------------------------------------------------
    @api.constrains("amount", "transfer_direction")
    def _check_transfer_amount_positive(self):
        for line in self.filtered("transfer_direction"):
            if (line.amount or 0.0) <= 0:
                raise ValidationError(_("Transfer amount must be greater than zero"))

    @api.constrains(
        "transfer_direction",
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
    )
    def _check_supplementary_dims_exclusive(self):
        for line in self.filtered("transfer_direction"):
            if line.kmitl_project_analytic_id and line.procurement_plan_analytic_id:
                raise ValidationError(
                    _(
                        "Each line may carry only one supplementary dimension — "
                        "KMITL Project or Procurement Plan, not both."
                    )
                )

    @api.constrains(
        "transfer_direction",
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
        "account_id",
    )
    def _check_supplementary_dims_match_account(self):
        account_model = self.env["budget.account"]
        has_proc = "procurement_plan" in account_model._fields
        for line in self.filtered("transfer_direction"):
            account = line.account_id
            if not account:
                continue
            if line.kmitl_project_analytic_id and not (
                "is_project" in account._fields and account.is_project
            ):
                raise ValidationError(
                    _(
                        "The Project/Activity dimension may only be used with "
                        "project-type budget accounts (is_project)."
                    )
                )
            if line.procurement_plan_analytic_id and not (
                has_proc and account.procurement_plan
            ):
                raise ValidationError(
                    _(
                        "The Procurement Plan dimension may only be used with "
                        "procurement-plan-type budget accounts."
                    )
                )

    @api.constrains("transfer_direction", "account_id", "analytic_distribution")
    def _check_transfer_duplicate_lines(self):
        for line in self.filtered("transfer_direction"):
            if not line.account_id:
                continue
            duplicate = self.search(
                [
                    ("move_id", "=", line.move_id.id),
                    ("transfer_direction", "=", line.transfer_direction),
                    ("account_id", "=", line.account_id.id),
                    ("analytic_distribution", "=", line.analytic_distribution),
                    ("id", "!=", line.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _(
                        "Duplicate transfer line found. Each combination of "
                        "direction, budget account and analytic distribution must "
                        "be unique."
                    )
                )
