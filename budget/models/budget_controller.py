import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetController(models.AbstractModel):
    """Unified budget availability engine (set-based, control-node).

    Single source of truth for "available budget" (ADR 0005). Availability for a
    reservation against ``(budget.account × analytic_distribution)`` is:

        available = current − used

    evaluated at the **control node** on every hierarchical axis — the nearest
    budgetable ancestor-or-self that actually carries posted appropriation —
    with both current and used rolled up over that node's subtree. Usually the
    control node is the reserved node itself; for coarsely-budgeted lines
    (งบบุคลากร / งบโครงการ, appropriated at an upper node) it walks up. Direction
    is one-way: appropriation may sit at or above the reservation, never below.

    - ``current`` = Σ posted ``budget.move.line.balance`` (appropriation + entry).
    - ``used``    = Σ posted ``reserve`` lines of active commitments
      (reserved/partial/done). obligate/consume are a waterfall *under* reserve
      (ADR 0001), so they are not subtracted again here.
    - The result is **not floored**: a negative value means over-committed.

    Matching is set-based (``read_group`` + ``child_of``) on stored columns, so
    every controlled dimension needs a column — see ``_DIM_COLUMNS`` and ADR 0005
    (decision G1). The public entry point takes ``analytic_distribution`` (JSON),
    so the engine is dimension-agnostic.

    Case A (one funded level per chain per axis) is assumed; Case B
    (multiple funded levels on one chain) is deferred — see ADR 0005.
    """

    _name = "budget.controller"
    _description = "Budget Availability Engine"

    # Posted move types that build the appropriated pool (incl. transfers).
    _APPROPRIATION_MOVE_TYPES = ("appropriation", "entry")
    # Commitment states whose reserve lines still lock budget.
    _ACTIVE_COMMITMENT_STATES = ("reserved", "partial", "done")
    # Analytic plan code -> stored column on the budget line models. The only
    # place a dimension is named; add a controlled dimension by adding a stored
    # column + one entry here (ADR 0005, G1).
    _DIM_COLUMNS = {
        "departments": "department_analytic_id",
        "sources": "source_analytic_id",
        "funds": "fund_analytic_id",
        "activities": "activity_analytic_id",
        "kmitl_project": "kmitl_project_analytic_id",
        "procurement_plan": "procurement_plan_analytic_id",
    }
    # "Ownership tag" dimensions: they identify the document that owns a
    # reservation (a project / a procurement plan) and ride on its reserve lines,
    # but the appropriation pool a project draws from is *untagged* (floating,
    # ADR-0007). So they are pinned absent on the appropriation (current) side
    # only; on the usage side a floating check must count every reserve drawing
    # from the pool whatever its owner, else it ignores other documents' reserves
    # and overstates what is available — letting projects over-reserve the pool.
    _POOL_TAG_COLUMNS = (
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @api.model
    def get_available(
        self, budget_account, analytic_distribution, fiscal_year_id, company_id=None
    ):
        """Available budget for ``(budget_account × analytic_distribution)``.

        ``budget_account`` may be an id or a ``budget.account`` record;
        ``analytic_distribution`` is the ``{analytic_account_id: percentage}``
        JSON. Returns ``current − used`` at the control node (not floored).
        """
        if not company_id:
            company_id = self.env.company.id
        account = self._coerce_account(budget_account)
        if not account or not fiscal_year_id:
            return 0.0
        dims = self._parse_dimensions(analytic_distribution)
        controls = self._resolve_control_nodes(
            account, dims, fiscal_year_id, company_id
        )
        current = self._sum_current(controls, dims, fiscal_year_id, company_id)
        used = self._sum_used(controls, dims, fiscal_year_id, company_id)
        return current - used

    @api.model
    def get_available_budget(self, analytic_data, fiscal_year_id, company_id=None):
        """Backward-compatible wrapper over :meth:`get_available`.

        Converts the legacy ``analytic_data`` dict
        (``{account_id, *_analytic_id}``) into ``analytic_distribution`` and
        delegates. Kept for the existing callers (commitment mixin, transfers).
        """
        if not company_id:
            company_id = self.env.company.id
        analytic_distribution = {}
        for column in self._DIM_COLUMNS.values():
            value = analytic_data.get(column)
            if value:
                analytic_distribution[str(value)] = 100.0
        return self.get_available(
            analytic_data.get("account_id"),
            analytic_distribution,
            fiscal_year_id,
            company_id,
        )

    @api.model
    def check_budget_availability(
        self, analytic_data, amount, fiscal_year_id, company_id=None
    ):
        """Raise ``ValidationError`` if ``amount`` exceeds available budget."""
        if not company_id:
            company_id = self.env.company.id
        available_amount = self.get_available_budget(
            analytic_data, fiscal_year_id, company_id
        )
        if amount > available_amount:
            raise ValidationError(
                self._format_budget_shortage_message(
                    analytic_data, available_amount, amount
                )
            )
        return True

    # ------------------------------------------------------------------
    # Control-node resolution + set-based aggregation
    # ------------------------------------------------------------------
    def _coerce_account(self, budget_account):
        """Accept an id or a record; return a (possibly empty) budget.account."""
        if not budget_account:
            return self.env["budget.account"].browse()
        if isinstance(budget_account, models.BaseModel):
            return budget_account[:1]
        return self.env["budget.account"].browse(int(budget_account)).exists()

    def _parse_dimensions(self, analytic_distribution):
        """``{analytic_id: pct}`` -> ``{line_column: analytic.account}``.

        Only dimensions that map to a known column (``_DIM_COLUMNS``) participate;
        the plan a value belongs to is read from the analytic account itself, so
        nothing is hard-coded per dimension.
        """
        result = {}
        if not analytic_distribution:
            return result
        analytic = self.env["account.analytic.account"]
        for raw_id in analytic_distribution:
            account = analytic.browse(int(raw_id)).exists()
            if not account:
                continue
            column = self._DIM_COLUMNS.get(account.plan_id.code)
            if column:
                result[column] = account
        return result

    @staticmethod
    def _self_and_ancestor_ids(record):
        """ids along ``parent_path`` (root-first), including the record itself."""
        ids = [
            int(x) for x in (record.parent_path or "").strip("/").split("/") if x
        ]
        return ids or record.ids

    def _appropriation_domain(self, fiscal_year_id, company_id):
        return [
            ("parent_state", "=", "posted"),
            ("move_type", "in", list(self._APPROPRIATION_MOVE_TYPES)),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("company_id", "=", company_id),
        ]

    def _resolve_control_nodes(self, account, dims, fiscal_year_id, company_id):
        """Find the funded control node on each axis (ADR 0005, Case A).

        For the account and each hierarchical dimension, walk from the
        reservation value up its ancestors and stop at the nearest level that
        carries appropriation of its own. Appropriation may sit at or above the
        reservation on every dimension (the ``covering`` leaves), so a coarse
        allocation tagged at a parent value still resolves the funded level.
        """
        base = self._appropriation_domain(fiscal_year_id, company_id)
        move_line = self.env["budget.move.line"]

        # appropriation may carry each dimension at-or-above the reservation's;
        # dimensions the reservation does NOT use must be empty, otherwise
        # appropriation carrying any value there would leak in (cross-dimension).
        covering = [
            (column, "in", self._self_and_ancestor_ids(acc))
            for column, acc in dims.items()
        ] + self._absent_dim_leaves(dims)

        # account axis: nearest ancestor-or-self with its own appropriation
        control_account = account
        for node_id in reversed(self._self_and_ancestor_ids(account)):
            if move_line.search_count(
                base + [("account_id", "=", node_id)] + covering
            ):
                control_account = self.env["budget.account"].browse(node_id)
                break

        # each dimension axis, scoped to the resolved account subtree
        control_dims = {}
        for column, acc in dims.items():
            control = acc
            others = [
                leaf for leaf in covering if leaf[0] != column
            ]
            for node_id in reversed(self._self_and_ancestor_ids(acc)):
                if move_line.search_count(
                    base
                    + [
                        ("account_id", "child_of", control_account.id),
                        (column, "=", node_id),
                    ]
                    + others
                ):
                    control = self.env["account.analytic.account"].browse(node_id)
                    break
            control_dims[column] = control

        return {"account": control_account, "dims": control_dims}

    def _analytic_hier_op(self):
        """``child_of`` when analytic accounts are hierarchical, else ``=``.

        Mirrors the dashboard's guard: the analytic hierarchy comes from the OCA
        ``account_analytic_parent`` module; without it the dimensions are flat
        and must match exactly. ``budget.account`` is always hierarchical here.
        """
        return (
            "child_of"
            if "parent_id" in self.env["account.analytic.account"]._fields
            else "="
        )

    def _absent_dim_leaves(self, dims, include_pool_tags=True):
        """Require controlled dimensions NOT used by this reservation to be empty.

        Without this, a combination that omits a dimension would match
        appropriation/usage carrying *any* value there (cross-dimension leak).
        ``kmitl_project`` and ``procurement_plan`` are mutually exclusive, so the
        unused one is correctly required to be empty.

        ``include_pool_tags=False`` leaves the ownership tags
        (:attr:`_POOL_TAG_COLUMNS`) unpinned — used on the *usage* side so a
        floating-pool check counts every reserve drawing from the (untagged)
        pool whatever document owns it; they stay pinned on the appropriation
        side. The four real dimensions are pinned either way.
        """
        skip = () if include_pool_tags else self._POOL_TAG_COLUMNS
        return [
            (column, "=", False)
            for column in self._DIM_COLUMNS.values()
            if column not in dims and column not in skip
        ]

    def _control_scope(self, controls, dims, include_pool_tags=True):
        """Subtree leaves over the control node on every axis.

        ``child_of`` rolls usage/appropriation up to the control node so sibling
        draws cannot double-spend a shared pool; flat analytic dimensions fall
        back to an exact match. Unused dimensions are pinned empty, except the
        ownership tags when ``include_pool_tags=False`` (see
        :meth:`_absent_dim_leaves`).
        """
        dim_op = self._analytic_hier_op()
        leaves = [("account_id", "child_of", controls["account"].id)]
        for column in dims:
            leaves.append((column, dim_op, controls["dims"][column].id))
        return leaves + self._absent_dim_leaves(
            dims, include_pool_tags=include_pool_tags
        )

    def _sum_current(self, controls, dims, fiscal_year_id, company_id):
        """Σ posted appropriation/entry balance over the control-node subtree."""
        domain = self._appropriation_domain(fiscal_year_id, company_id)
        domain += self._control_scope(controls, dims)
        groups = self.env["budget.move.line"].read_group(domain, ["balance"], [])
        return (groups[0].get("balance") or 0.0) if groups else 0.0

    def _sum_used(self, controls, dims, fiscal_year_id, company_id):
        """Σ posted reserve amounts of active commitments over the subtree."""
        domain = [
            ("state", "=", "posted"),
            ("move_type", "=", "reserve"),
            ("commitment_id.state", "in", list(self._ACTIVE_COMMITMENT_STATES)),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("company_id", "=", company_id),
        ]
        # Count every reserve drawing from the pool regardless of which project /
        # plan owns it: the floating appropriation is untagged, so pinning the
        # ownership tags here would drop other documents' reserves and overstate
        # availability (the over-reservation bug).
        domain += self._control_scope(controls, dims, include_pool_tags=False)
        groups = self.env["budget.commitment.line"].read_group(
            domain, ["amount"], []
        )
        return (groups[0].get("amount") or 0.0) if groups else 0.0

    def _format_budget_shortage_message(
        self, analytic_data, available_amount, requested_amount
    ):
        """Format detailed budget shortage error message"""
        account = self.env["budget.account"].browse(
            analytic_data.get("account_id")
        )
        activity = self.env["account.analytic.account"].browse(
            analytic_data.get("activity_analytic_id")
        )
        department = self.env["account.analytic.account"].browse(
            analytic_data.get("department_analytic_id")
        )
        fund = self.env["account.analytic.account"].browse(
            analytic_data.get("fund_analytic_id")
        )
        source = self.env["account.analytic.account"].browse(
            analytic_data.get("source_analytic_id")
        )

        return _(
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
            "account": account.display_name if account else "N/A",
            "activity": activity.display_name if activity else "N/A",
            "department": department.display_name if department else "N/A",
            "fund": fund.display_name if fund else "N/A",
            "source": source.display_name if source else "N/A",
            "available": available_amount,
            "requested": requested_amount,
            "shortage": requested_amount - available_amount,
        }

    # ------------------------------------------------------------------
    # Service write ops (unchanged — out of scope of the engine refactor)
    # ------------------------------------------------------------------
    @api.model
    def reserve_budget(
        self,
        analytic_data,
        amount,
        fiscal_year_id,
        source_record=None,
        company_id=None,
    ):
        """Reserve budget by creating a commitment with a reserve line"""
        if not company_id:
            company_id = self.env.company.id

        self.check_budget_availability(
            analytic_data, amount, fiscal_year_id, company_id
        )

        commitment_data = self._prepare_service_commitment_data(
            analytic_data, amount, fiscal_year_id, source_record, company_id
        )

        commitment = self.env["budget.commitment"].create(commitment_data)
        commitment.action_reserve()

        _logger.info(
            "Reserved budget amount %s via service for %s",
            amount,
            source_record._name if source_record else "service",
        )

        return commitment

    @api.model
    def consume_budget(self, commitment_id, amount=None, source_record=None):
        """Consume budget by adding a consume line to the commitment"""
        commitment = self.env["budget.commitment"].browse(commitment_id)

        if not commitment.exists():
            raise UserError(_("Budget commitment not found."))

        if commitment.state not in ["reserved", "partial"]:
            raise UserError(
                _(
                    "Budget commitment must be in reserved or partial state to consume."
                )
            )

        # Get first reserve line for analytic info
        first_reserve = commitment.line_ids.filtered(
            lambda l: l.move_type == "reserve" and l.state == "posted"
        )[:1]

        if not first_reserve:
            raise UserError(_("No active reserve lines found on commitment."))

        consume_amount = (
            amount if amount else commitment.available_to_consume
        )

        consume_line = self.env["budget.commitment.line"].create(
            {
                "commitment_id": commitment.id,
                "move_type": "consume",
                "account_id": first_reserve.account_id.id,
                "analytic_distribution": first_reserve.analytic_distribution,
                "amount": consume_amount,
                "name": _("Service consumption for %s")
                % (source_record._name if source_record else "system"),
            }
        )

        _logger.info(
            "Consumed budget amount %s from commitment %s via service",
            consume_amount,
            commitment.name,
        )

        return consume_line

    @api.model
    def _prepare_service_commitment_data(
        self, analytic_data, amount, fiscal_year_id, source_record, company_id
    ):
        """Prepare commitment data for service-created commitments"""
        commitment_name = _("Service Commitment")
        if source_record:
            commitment_name = _("Commitment for %s") % (
                getattr(source_record, "name", None)
                or "%s #%s" % (source_record._description, source_record.id)
            )

        # Build analytic_distribution for the line
        analytic_dist = {}
        if analytic_data.get("activity_analytic_id"):
            analytic_dist[str(analytic_data["activity_analytic_id"])] = 100.0
        if analytic_data.get("fund_analytic_id"):
            analytic_dist[str(analytic_data["fund_analytic_id"])] = 100.0

        line_vals = {
            "move_type": "reserve",
            "account_id": analytic_data.get("account_id"),
            "analytic_distribution": analytic_dist or False,
            "amount": amount,
            "name": _("Service reservation for %s")
            % (source_record._name if source_record else "system"),
        }

        # Build header analytic_distribution (department + source)
        header_dist = {}
        if analytic_data.get("department_analytic_id"):
            header_dist[str(analytic_data["department_analytic_id"])] = 100.0
        if analytic_data.get("source_analytic_id"):
            header_dist[str(analytic_data["source_analytic_id"])] = 100.0

        return {
            "name": commitment_name,
            "date": fields.Date.today(),
            "analytic_distribution": header_dist or False,
            "account_fiscal_year_id": fiscal_year_id,
            "company_id": company_id,
            "currency_id": self.env.company.currency_id.id,
            "amount": amount,
            "line_ids": [(0, 0, line_vals)],
        }
