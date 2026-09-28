import logging
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class BudgetController(models.AbstractModel):
    """Unified budget availability engine (set-based, control-node).

    Single source of truth for "available budget" (ADR 0005). Availability for a
    reservation against ``(budget.account × analytic_distribution)`` is:

        available = current − used

    evaluated at the **control node** — the single funded coordinate at or above
    the reservation on **every** axis at once (account + each controlled
    dimension) — with both current and used rolled up over that node's subtree.
    Usually the control node is the reservation's own coordinate; for
    coarsely-budgeted lines (งบบุคลากร / งบโครงการ, appropriated at an upper
    node) or a descendant-code draw it sits above on one or more axes. Direction
    is one-way: appropriation may sit at or above the reservation, never below;
    nothing funded at/above it means 0 available.

    - ``current`` = Σ posted ``budget.move.line.balance`` (appropriation + entry).
    - ``used``    = Σ posted ``reserve`` lines of active commitments
      (reserved/partial/done). obligate/consume are a waterfall *under* reserve
      (ADR 0001), so they are not subtracted again here.
    - The result is **not floored**: a negative value means over-committed.

    Matching is set-based (``read_group`` + ``child_of``) on stored columns, so
    every controlled dimension needs a column — see ``_DIM_COLUMNS`` and ADR 0005
    (decision G1). The public entry point takes ``analytic_distribution`` (JSON),
    so the engine is dimension-agnostic.

    Pools never nest (ADR-0016): the nesting guard (:meth:`_check_pool_nesting`)
    forbids two funded coordinates comparable on every axis, so at most one pool
    covers a reservation.
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
        Thin wrapper over :meth:`get_available_detail`.
        """
        return self.get_available_detail(
            budget_account, analytic_distribution, fiscal_year_id, company_id
        )["available"]

    @api.model
    def get_available_detail(
        self, budget_account, analytic_distribution, fiscal_year_id, company_id=None
    ):
        """Available budget plus the resolved pool coordinate.

        Returns ``{"available": float, "pool": {...} | None}``. ``pool`` names the
        funded control node (account + each controlled dimension) the figure was
        read at, for the reservation picker's "งบที่จองได้ … (คุมงบที่ …)" line.
        When no funded coordinate covers the reservation (uncovered), ``pool`` is
        ``None`` and ``available`` is 0.0 (ADR-0016, fixes the downward leak H1).
        """
        if not company_id:
            company_id = self.env.company.id
        account = self._coerce_account(budget_account)
        if not account or not fiscal_year_id:
            return {"available": 0.0, "pool": None}
        dims = self._parse_dimensions(analytic_distribution)
        controls = self._resolve_control_nodes(
            account, dims, fiscal_year_id, company_id
        )
        if controls is None:
            return {"available": 0.0, "pool": None}
        current = self._sum_current(controls, dims, fiscal_year_id, company_id)
        used = self._sum_used(controls, dims, fiscal_year_id, company_id)
        return {
            "available": current - used,
            "pool": self._pool_descriptor(controls),
        }

    def _pool_descriptor(self, controls):
        """A JSON-safe description of the resolved control node, for the picker."""
        account = controls["account"]
        return {
            "account": {
                "id": account.id,
                "code": account.code,
                "display_name": account.display_name,
            },
            "dims": {
                column: {
                    "id": acc.id,
                    "code": acc.code,
                    "display_name": acc.display_name,
                }
                for column, acc in controls["dims"].items()
                if acc
            },
        }

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

    def _pool_rounding(self, company_id):
        """Company-currency rounding used to decide whether a net is a pool."""
        company = self.env["res.company"].browse(company_id)
        currency = company.currency_id or self.env.company.currency_id
        return currency.rounding or 0.01

    def _resolve_control_nodes(self, account, dims, fiscal_year_id, company_id):
        """Find the single funded control node covering the reservation.

        The control node is the one funded coordinate at or above the reservation
        on **every** axis at once (account + each controlled dimension), read in a
        single grouped query (ADR-0016). "Funded" means the net posted
        appropriation+entry at that coordinate is not zero. Because pools never
        nest (enforced by :meth:`_check_pool_nesting`), at most one such
        coordinate covers a reservation.

        Returns ``{"account": budget.account, "dims": {column: analytic}}`` or
        ``None`` when nothing funds the reservation (uncovered → 0 available;
        this is the H1 downward-leak fix — a bare reservation node no longer
        defaults to itself and sweeps in every pool below it).
        """
        base = self._appropriation_domain(fiscal_year_id, company_id)
        # account and each used dimension may sit at-or-above the reservation;
        # dimensions the reservation does NOT use must be empty, else a pool
        # carrying any value there would leak in (cross-dimension).
        domain = base + [
            ("account_id", "in", self._self_and_ancestor_ids(account))
        ]
        for column, acc in dims.items():
            domain.append((column, "in", self._self_and_ancestor_ids(acc)))
        domain += self._absent_dim_leaves(dims)

        groupby = ["account_id"] + list(dims.keys())
        rounding = self._pool_rounding(company_id)
        funded = []
        for grp in self.env["budget.move.line"].read_group(
            domain, ["balance"], groupby, lazy=False
        ):
            acc_id = (grp.get("account_id") or [None])[0]
            if not acc_id:
                continue
            if float_is_zero(grp.get("balance") or 0.0, precision_rounding=rounding):
                continue
            coord = {"account": acc_id}
            for column in dims:
                coord[column] = (grp.get(column) or [False])[0]
            funded.append(coord)

        if not funded:
            return None
        if len(funded) > 1:
            # Legacy nested pools (created before the guard). Pick the deepest so
            # the tighter pool controls, and warn — the scan reports the overlap.
            funded.sort(key=self._coord_depth, reverse=True)
            _logger.warning(
                "budget.controller: %d funded coordinates cover the reservation "
                "on account %s (nested pools); using the deepest. Run "
                "scan_pool_overlaps.",
                len(funded),
                account.display_name,
            )
        coord = funded[0]
        control_account = self.env["budget.account"].browse(coord["account"])
        control_dims = {}
        analytic = self.env["account.analytic.account"]
        for column in dims:
            value = coord.get(column)
            control_dims[column] = analytic.browse(value) if value else analytic
        return {"account": control_account, "dims": control_dims}

    def _coord_depth(self, coord):
        """Total hierarchy depth of a funded coordinate (deeper = more specific)."""
        total = len(
            self._self_and_ancestor_ids(
                self.env["budget.account"].browse(coord["account"])
            )
        )
        analytic = self.env["account.analytic.account"]
        for column, value in coord.items():
            if column == "account" or not value:
                continue
            total += len(self._self_and_ancestor_ids(analytic.browse(value)))
        return total

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
        # sudo: a shared pool may carry reservations from other operating units
        # (ADR-0011/0016). Counting them can only *lower* Available, never leak
        # budget, so the OU fence is dropped on the usage side only.
        groups = self.env["budget.commitment.line"].sudo().read_group(
            domain, ["amount"], []
        )
        return (groups[0].get("amount") or 0.0) if groups else 0.0

    # ------------------------------------------------------------------
    # Pool-nesting guard (กองงบไม่ซ้อน) — ADR-0016
    # ------------------------------------------------------------------
    def _pool_coord_columns(self):
        """The ordered stored columns that make a pool coordinate (account + 6)."""
        return ["account_id"] + list(self._DIM_COLUMNS.values())

    def _lines_to_candidates(self, lines):
        """budget.move.line recordset -> candidate deltas for the guard.

        Each candidate is ``{"account_id": id, <dim column>: id|False,
        "balance": float}`` — the coordinate the line posts to and its signed
        balance delta.
        """
        columns = list(self._DIM_COLUMNS.values())
        candidates = []
        for line in lines:
            cand = {
                "account_id": line.account_id.id,
                "balance": line.balance or 0.0,
            }
            for column in columns:
                cand[column] = line[column].id or False
            candidates.append(cand)
        return candidates

    def _candidate_coord(self, candidate):
        """Ordered coordinate tuple (account + 6 dims) for a candidate/group."""
        return (candidate.get("account_id") or False,) + tuple(
            candidate.get(column) or False for column in self._DIM_COLUMNS.values()
        )

    def _posted_pool_state(self, fiscal_year_id, company_id):
        """{coord tuple: net balance} of posted expense appropriation/entry.

        One sudo ``read_group`` over the 7 pool columns for the whole fiscal year
        (every operating unit), so the nesting picture is complete.
        """
        columns = self._pool_coord_columns()
        domain = self._appropriation_domain(fiscal_year_id, company_id) + [
            ("budget_type", "=", "expense")
        ]
        state = defaultdict(float)
        for grp in self.env["budget.move.line"].sudo().read_group(
            domain, ["balance"], columns, lazy=False
        ):
            account = (grp.get("account_id") or [None])[0]
            if not account:
                continue
            coord = (account,) + tuple(
                (grp.get(column) or [False])[0]
                for column in self._DIM_COLUMNS.values()
            )
            state[coord] += grp.get("balance") or 0.0
        return state

    def _pool_index(self, coords):
        """Index pool coordinates for comparable lookups (ADR-0016).

        Parent paths are read once for every account / analytic value in
        ``coords``; pools are indexed by their exact account and by every
        account on that account's path, so only pools on the same account chain
        are ever compared.
        """
        accounts = self.env["budget.account"].browse(
            list({c[0] for c in coords if c[0]})
        )
        analytics = self.env["account.analytic.account"].browse(
            list({value for c in coords for value in c[1:] if value})
        )
        acc_path = {r.id: set(self._self_and_ancestor_ids(r)) for r in accounts}
        ana_path = {r.id: set(self._self_and_ancestor_ids(r)) for r in analytics}
        by_account = defaultdict(list)  # exact account -> pools
        by_path = defaultdict(list)  # account on the path -> pools at/below it
        for coord in coords:
            by_account[coord[0]].append(coord)
            for anc in acc_path.get(coord[0], ()):
                by_path[anc].append(coord)
        return acc_path, ana_path, by_account, by_path

    def _comparable_pools(self, coord, index):
        """Yield indexed pools comparable to ``coord`` on **every** axis.

        Comparable = equal, or one an ancestor of the other; ``False`` only
        equals ``False`` (a tagged and an untagged pool never conflict —
        ADR-0012). ``coord`` itself is excluded (identical is not nesting).
        """
        acc_path, ana_path, by_account, by_path = index
        candidates = set(by_path[coord[0]])  # same account or below
        for anc in acc_path.get(coord[0], ()):  # above
            candidates.update(by_account[anc])
        candidates.discard(coord)
        for other in candidates:
            if all(
                x == y or (x and y and (x in ana_path[y] or y in ana_path[x]))
                for x, y in zip(coord[1:], other[1:])
            ):
                yield other

    def _check_pool_nesting(self, candidates, fiscal_year_id, company_id):
        """Raise if posting ``candidates`` would leave two comparable pools.

        ``candidates`` is a list of delta dicts (see :meth:`_lines_to_candidates`).
        The posted state after applying the deltas is computed, then any
        coordinate that is new or topped up and still non-zero must not be
        comparable to another non-zero pool (ADR-0016, กองงบไม่ซ้อน). Draining a
        pool never trips the guard.
        """
        if not candidates or not fiscal_year_id:
            return
        rounding = self._pool_rounding(company_id)
        state = self._posted_pool_state(fiscal_year_id, company_id)
        touched = set()
        for candidate in candidates:
            coord = self._candidate_coord(candidate)
            delta = candidate.get("balance") or 0.0
            was_zero = float_is_zero(state[coord], precision_rounding=rounding)
            state[coord] += delta
            # new pool (was zero) or topped up (positive delta): worth checking.
            if delta > 0 or was_zero:
                touched.add(coord)
        nonzero = {
            coord
            for coord, net in state.items()
            if not float_is_zero(net, precision_rounding=rounding)
        }
        index = self._pool_index(nonzero)
        for coord in touched:
            if coord not in nonzero:
                continue
            for other in self._comparable_pools(coord, index):
                raise ValidationError(self._pool_nesting_message(coord, other))

    def scan_pool_overlaps(self, fiscal_year_id, company_id=None):
        """Read-only list of nested (comparable) pool pairs for a fiscal year.

        Used by the upgrade check and before deploy to find legacy overlaps the
        guard would now reject. Returns a list of ``(coord_a, coord_b)`` tuples.
        """
        if not company_id:
            company_id = self.env.company.id
        rounding = self._pool_rounding(company_id)
        state = self._posted_pool_state(fiscal_year_id, company_id)
        nonzero = [
            coord
            for coord, net in state.items()
            if not float_is_zero(net, precision_rounding=rounding)
        ]
        index = self._pool_index(nonzero)
        pairs = set()
        for coord in nonzero:
            for other in self._comparable_pools(coord, index):
                pairs.add(tuple(sorted((coord, other))))
        return sorted(pairs)

    def _coord_label(self, coord):
        """Human label ``account [dim=code …]`` for a pool coordinate."""
        account = self.env["budget.account"].browse(coord[0])
        parts = [account.display_name or account.code or str(coord[0])]
        analytic = self.env["account.analytic.account"]
        for column, value in zip(self._DIM_COLUMNS.values(), coord[1:]):
            if value:
                parts.append(
                    "%s=%s" % (column, analytic.browse(value).display_name)
                )
        return " / ".join(parts)

    def _pool_nesting_message(self, coord, other):
        return _(
            "กองงบประมาณซ้อนกันไม่ได้ (pools may not nest):\n"
            "- %(a)s\n"
            "- %(b)s\n"
            "จัดสรร/โอนงบไปที่รหัสของกองงบเดียว หรือใช้รหัสที่ไม่ทับซ้อนกับกองงบเดิม"
        ) % {"a": self._coord_label(coord), "b": self._coord_label(other)}

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
            # title is required on budget.commitment; the service path already
            # derives a human label for the (legacy) name, so reuse it.
            "title": commitment_name,
            "date": fields.Date.today(),
            "analytic_distribution": header_dist or False,
            "account_fiscal_year_id": fiscal_year_id,
            "company_id": company_id,
            "currency_id": self.env.company.currency_id.id,
            "amount": amount,
            "line_ids": [(0, 0, line_vals)],
        }
