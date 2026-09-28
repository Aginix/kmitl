import itertools
import logging
from collections import defaultdict

from odoo import api, models
from odoo.tools import float_is_zero, format_date

_logger = logging.getLogger(__name__)


class BudgetDashboard(models.AbstractModel):
    """Read-only aggregation service for the budget monitoring dashboard.

    Rows = a ``budget.account`` subtree (expense only). Each column is built from
    set-based ``read_group`` queries and then rolled up over the tree via
    ``parent_path`` (every cell of a parent = sum of itself + all descendants).

    It deliberately does NOT reuse ``budget.controller`` per-combination matching,
    which is O(N) per cell and meant for single availability checks.

    Columns (all expense):
        initial    (1) งบต้นปี          posted appropriation moves, appropriation_type=initial
        adjustment (±)                  current - initial (supplementary + net transfers)
        current    (a) งบปัจจุบัน        posted appropriation + entry move lines (incl. transfers)
        cap        (3) ขอใช้ทั้งหมด      Σ active commitment caps
        reserved   (b) เงินจอง           Σreserve - Σobligate   (commitment lines)
        obligated  (c) ผูกพัน            Σobligate - Σconsume
        consumed   (d) เบิกจ่าย          Σconsume
        used       (e) รวม              b + c + d  (= Σreserve, net of returns)
        remaining  (f) คงเหลือ           current - used
        returned   (g) ส่งคืนเงินเหลือจ่าย  Σ คืนจอง (negative reserve, is_return), shown positive
    """

    _name = "budget.dashboard"
    _description = "Budget Monitoring Dashboard"

    _DIM_FIELDS = (
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    )
    # Per-dimension key-segment prefix for breakdown row keys (e.g. "a5|p12|b9").
    _DIM_KEY_SEG = {
        "activity_analytic_id": "a",
        "department_analytic_id": "p",
        "fund_analytic_id": "f",
        "source_analytic_id": "s",
    }
    _ACTIVE_COMMITMENT_STATES = ("reserved", "partial", "done")
    # The seven own figures every row is built from (see _value_columns), and
    # the usage-side subset that is folded onto its covering pool (ADR-0016).
    _FACT_KEYS = (
        "initial",
        "current",
        "cap",
        "reserved",
        "obligated",
        "consumed",
        "returned",
    )
    _USAGE_KEYS = ("cap", "reserved", "obligated", "consumed", "returned")
    # Fixed display order for the top-level expense budget categories.
    _ROOT_ORDER = ("51000", "52000", "53000", "54000", "55000", "07020")
    # Rows shown per recent-movement table on the overview landing page.
    _RECENT_LIMIT = 6
    _OVERVIEW_KEYS = (
        "initial",
        "adjustment",
        "current",
        "cap",
        "reserved",
        "obligated",
        "consumed",
        "used",
        "remaining",
    )
    # Monthly time-series move types (จอง / ผูกพัน / เบิกจ่าย) + Thai month labels.
    _TS_MOVE_TYPES = ("reserve", "obligate", "consume")
    _THAI_MONTH_ABBR = (
        "ม.ค.",
        "ก.พ.",
        "มี.ค.",
        "เม.ย.",
        "พ.ค.",
        "มิ.ย.",
        "ก.ค.",
        "ส.ค.",
        "ก.ย.",
        "ต.ค.",
        "พ.ย.",
        "ธ.ค.",
    )

    @api.model
    def get_dashboard_data(
        self,
        fiscal_year_id,
        root_account_id=None,
        filters=None,
        breakdown=None,
    ):
        """Return ``{"rows": [...], "currency_id": id}`` for the dashboard grid.

        ``breakdown`` (optional) is an analytic dimension field name, or an
        ordered list of them (e.g. ``["activity_analytic_id",
        "department_analytic_id"]``). When set, the budget-account tree is
        nested under those dimensions' hierarchies (outer to inner) — same
        columns, same roll-up — instead of being the sole row axis. See
        :meth:`_breakdown_rows`.

        Figures are read at the **pool** (ADR-0016, amending ADR-0008): usage
        (cap / reserve / obligate / consume / return) booked at a Descendant
        Code is folded onto the tuple of the Budget Pool that covers it, so a
        pool row's คงเหลือ is what can still be reserved there. A hierarchical
        dimension filter therefore also surfaces the pools *covering* the typed
        code (its ancestors as well as its ``child_of`` subtree), each with its
        whole usage; the ancestor chain of each filter value is returned as
        ``filter_ancestors`` (drill-down + the picker's finer-code pin). Rows
        whose usage was folded carry ``usage_in`` / ``usage_out`` coordinate
        pairs so a usage drill-down lists exactly the lines behind the figure.
        """
        filters = filters or {}
        currency_id = self.env.company.currency_id.id
        if not fiscal_year_id:
            return {"rows": [], "currency_id": currency_id}

        accounts = self._dashboard_accounts(root_account_id)
        if not accounts:
            return {"rows": [], "currency_id": currency_id}
        account_ids = accounts.ids
        analytic = self.env["account.analytic.account"]
        # Dimension accounts are hierarchical (account_analytic_parent): a chosen
        # value matches itself + all descendants via child_of. Source is a flat
        # classification (exact match). Guarded in case the hierarchy is absent.
        hier_op = "child_of" if "parent_id" in analytic._fields else "="
        full = self._DIM_FIELDS
        exact_leaves = []  # flat filters: same on the appropriation + usage side
        cover_leaves = []  # appropriation side: filter subtree OR its ancestors
        scope = {}  # hierarchical filter field -> values (the usage scope)
        filter_ancestors = {}
        for fname in full:
            val = filters.get(fname)
            if not val:
                continue
            is_list = isinstance(val, (list, tuple))
            if fname == "source_analytic_id" or hier_op != "child_of":
                exact_leaves.append((fname, "in" if is_list else "=", val))
                continue
            values = list(val) if is_list else [val]
            ancestors = set()
            for rec in analytic.browse(values):
                ancestors.update(self._ancestor_ids(rec))
            filter_ancestors[fname] = sorted(ancestors)
            scope[fname] = values
            cover_leaves += [
                "|",
                (fname, "child_of", values),
                (fname, "in", sorted(ancestors)),
            ]

        # --- (a) current pool and (1) initial, from posted move lines ---
        move_base = [
            ("parent_state", "=", "posted"),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("account_id", "in", account_ids),
        ] + exact_leaves + cover_leaves
        current = self._facts_by_account_dims(
            "budget.move.line",
            move_base + [("move_type", "in", ("appropriation", "entry"))],
            "balance",
            full,
        )
        initial = self._facts_by_account_dims(
            "budget.move.line",
            move_base
            + [
                ("move_type", "=", "appropriation"),
                ("appropriation_type", "=", "initial"),
            ],
            "balance",
            full,
        )

        # --- usage: the filter subtree plus the whole subtree of every pool
        # above it (its usage from sibling codes counts against it too) ---
        rounding = self.env.company.currency_id.rounding or 0.01
        usage_leaves = []
        for fname, values in scope.items():
            i = full.index(fname)
            strict = set(filter_ancestors[fname]) - set(values)
            above = {
                tup[i]
                for (_acc, tup), bal in current.items()
                if tup[i] in strict
                and not float_is_zero(bal, precision_rounding=rounding)
            }
            usage_leaves.append((fname, "child_of", values + sorted(above)))
        cl_base = [
            ("state", "=", "posted"),
            ("commitment_id.state", "in", self._ACTIVE_COMMITMENT_STATES),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("account_id", "in", account_ids),
        ] + exact_leaves + usage_leaves
        # (3) approved cap = Σ active commitment caps. Header analytic dims are
        # non-stored, so when a dimension filter is set the matching commitments
        # are resolved through their stored lines.
        commit_domain = [
            ("state", "in", self._ACTIVE_COMMITMENT_STATES),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("account_id", "in", account_ids),
        ]
        if exact_leaves or usage_leaves:
            match = (
                self.env["budget.commitment.line"]
                .search(cl_base)
                .mapped("commitment_id")
            )
            commit_domain.append(("id", "in", match.ids))
        by_type = self._facts_by_account_dims_type(
            "budget.commitment.line", cl_base, "amount", full
        )
        sources = {
            "initial": initial,
            "current": current,
            "cap": self._cap_facts_by_account_dims(commit_domain, full),
            "reserved": by_type.get("reserve", {}),
            "obligated": by_type.get("obligate", {}),
            "consumed": by_type.get("consume", {}),
            # (g) ส่งคืนเงินเหลือจ่าย: the คืนจอง lines (negative reserve,
            # is_return), a memo column. The signed reserve bucket already nets
            # these in, so b/e/f drop/rise on their own once a return posts.
            "returned": self._facts_by_account_dims(
                "budget.commitment.line",
                cl_base + [("is_return", "=", True)],
                "amount",
                full,
            ),
        }
        own = {}
        for metric in self._FACT_KEYS:
            for key, val in sources[metric].items():
                own.setdefault(key, dict.fromkeys(self._FACT_KEYS, 0.0))[
                    metric
                ] = val
        acc_by_id = {acc.id: acc for acc in accounts}
        fold = self._fold_usage_to_pools(own, scope, acc_by_id, rounding)

        # Optional breakdown: nest the budget-account tree under one or more
        # analytic dimensions (ordered, e.g. activities then departments)
        # instead of using the account tree as the sole row axis.
        dims = self._normalize_breakdown(breakdown)
        if dims:
            rows = self._breakdown_rows(dims, accounts, account_ids, fold)
            return {
                "rows": rows,
                "currency_id": currency_id,
                "hier_op": hier_op,
                "filter_ancestors": filter_ancestors,
            }

        # flat report: collapse the folded tuples onto their account
        keys = self._FACT_KEYS
        by_account = defaultdict(lambda: dict.fromkeys(keys, 0.0))
        for (acc_id, _tup), vals in fold["own"].items():
            node = by_account[acc_id]
            for k in keys:
                node[k] += vals[k]
        # --- roll own values up the subtree via parent_path ---
        rolled = {aid: dict.fromkeys(keys, 0.0) for aid in account_ids}
        for acc in accounts:
            own = by_account.get(acc.id)
            if not own or not any(own.values()):
                continue
            for aid in self._ancestor_ids(acc):
                node = rolled.get(aid)
                if node is not None:
                    for k in keys:
                        node[k] += own[k]

        # Emit rows in depth-first pre-order built from parent_id. Ordering by
        # code alone is NOT a valid tree order (a deep child can sort before its
        # parent), which is what made the collapse/indentation render wrong.
        children = defaultdict(list)
        roots = []
        for acc in accounts:
            if acc.parent_id.id in acc_by_id:
                children[acc.parent_id.id].append(acc)
            else:
                roots.append(acc)
        # Top-level budget categories follow a fixed display order (mirrors the
        # dashboard's root dropdown); descendants stay in code order.
        order = self._ROOT_ORDER
        roots.sort(
            key=lambda a: (
                order.index(a.code) if a.code in order else len(order),
                a.code,
            )
        )

        rows = []
        stack = [(acc, 0) for acc in reversed(roots)]
        while stack:
            acc, level = stack.pop()
            kids = children.get(acc.id, [])
            row = self._make_row(acc, rolled[acc.id], level, bool(kids))
            if fold["moved"]:
                row.update(
                    self._usage_drill_pairs(
                        fold,
                        lambda acc_id, _tup, acc=acc: acc.id
                        in self._ancestor_ids(acc_by_id[acc_id]),
                    )
                )
            rows.append(row)
            for child in reversed(kids):
                stack.append((child, level + 1))
        return {
            "rows": rows,
            "currency_id": currency_id,
            "hier_op": hier_op,
            "filter_ancestors": filter_ancestors,
        }

    # ------------------------------------------------------------------
    # multi-dimension breakdown (e.g. activities)
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_breakdown(breakdown):
        """Coerce the ``breakdown`` param into an ordered dim-field list or None.

        Accepts ``None``/``False``/``[]`` (-> None, flat report), a single field
        name string (-> one-element list), or an ordered list of field names.
        """
        if not breakdown:
            return None
        if isinstance(breakdown, str):
            return [breakdown]
        dims = [d for d in breakdown if d]
        return dims or None

    def _breakdown_rows(self, dims, accounts, account_ids, fold):
        """Rows for an N-dimension breakdown nested over the budget-account tree.

        ``dims`` is an ordered list of analytic dimension fields, e.g.
        ``["activity_analytic_id", "department_analytic_id"]``. They form the
        outer hierarchy (activities outer, departments inner, …) and the
        budget-account subtree hangs off the innermost level. ADR-0008's
        exact-match rule applies at *every* level: under each exact dimension
        node the next dimension (or the account tree) is nested only for lines
        tagged to that exact node — never rolled down from an ancestor. A node's
        displayed figure is the sum over its whole remaining subtree, so every
        level reconciles with the flat report. Untagged values at any level fall
        into a per-level "ไม่ระบุ" sentinel (id 0). Keys are path-encoded and
        unique (e.g. ``a5|p12|b9``) so one account can appear under many tuples.

        ``fold`` is :meth:`_fold_usage_to_pools`'s result: facts on the full
        dimension tuple with usage already folded onto its pool's tuple (the
        ADR-0016 amendment), projected here onto ``dims``.
        """
        keys = self._FACT_KEYS
        full = self._DIM_FIELDS
        dims = [d for d in dims if d in full]
        idx = [full.index(d) for d in dims]

        def project(tup):
            return tuple(tup[i] for i in idx)

        # own[(account_id, dim_tuple)] = {metric: value}; 0 in a tuple = untagged
        # at that position. Each full-tuple fact projects onto exactly one tuple,
        # so money is never double-counted and Σ over tuples == the flat report.
        own = {}
        for (acc_id, tup), vals in fold["own"].items():
            node = own.setdefault((acc_id, project(tup)), dict.fromkeys(keys, 0.0))
            for metric in keys:
                node[metric] += vals[metric]
        ana_path = fold["ana_path"]
        moved = fold["moved"]
        # Index by full tuple so emit_account_tree need not rescan all facts.
        own_by_tuple = defaultdict(dict)
        for (acc_id, tup), vals in own.items():
            own_by_tuple[tup][acc_id] = vals

        acc_by_id = {a.id: a for a in accounts}
        account_id_set = set(account_ids)
        Analytic = self.env["account.analytic.account"]
        n = len(dims)

        # Full tuples and every prefix present, for O(1) "has deeper content".
        present_prefixes = {tup[:k] for (_a, tup) in own for k in range(1, n + 1)}

        # Per-position analytic hierarchy (paths/parent/children/rec) over the
        # dim values that actually appear at that position (+ their ancestors).
        present_by_pos = [set() for _ in range(n)]
        for _a, tup in own:
            for i, value in enumerate(tup):
                if value:
                    present_by_pos[i].add(value)
        pos = []
        for present_ids in present_by_pos:
            paths = {}
            union = set()
            for rec in Analytic.browse(list(present_ids)):
                path = [
                    int(x) for x in (rec.parent_path or "").strip("/").split("/") if x
                ]
                paths[rec.id] = path or [rec.id]
                union.update(paths[rec.id])
            parent = {}
            children = defaultdict(list)
            seen = defaultdict(set)
            for path in paths.values():
                for j, node in enumerate(path):
                    par = path[j - 1] if j else None
                    parent.setdefault(node, par)
                    if par is not None and node not in seen[par]:
                        seen[par].add(node)
                        children[par].append(node)
            pos.append(
                {
                    "paths": paths,
                    "parent": parent,
                    "children": children,
                    "rec": {r.id: r for r in Analytic.browse(list(union))},
                }
            )

        seg = self._DIM_KEY_SEG

        def dim_key(prefix):
            return "|".join(
                "%s%s" % (seg.get(dims[i], "d%d" % i), prefix[i])
                for i in range(len(prefix))
            )

        def code_of(depth, node_id):
            rec = pos[depth]["rec"].get(node_id)
            return (rec.code or "") if rec else ""

        rows = []

        def emit_account_tree(prefix, level):
            # Budget-account subtree for the EXACT full dim tuple == prefix.
            rolled = {}
            for acc_id, own_acc in own_by_tuple.get(prefix, {}).items():
                for anc in self._ancestor_ids(acc_by_id[acc_id]):
                    if anc not in account_id_set:
                        continue
                    node = rolled.setdefault(anc, dict.fromkeys(keys, 0.0))
                    for metric in keys:
                        node[metric] += own_acc[metric]
            children = defaultdict(list)
            roots = []
            for acc_id in rolled:
                pid = acc_by_id[acc_id].parent_id.id
                (children[pid] if pid in rolled else roots).append(acc_by_id[acc_id])
            roots.sort(key=self._root_sort_key)
            for kids in children.values():
                kids.sort(key=lambda a: a.code or "")
            dpath = dim_key(prefix)
            dims_map = {dims[i]: (prefix[i] or False) for i in range(n)}

            own_here = own_by_tuple.get(prefix, {})

            def emit_acc(account, lvl):
                kids = children.get(account.id, [])
                pid = account.parent_id.id
                # own_current = this account's own posted current at the EXACT
                # tuple (not rolled down from children), so the picker can tell a
                # real pool row from a pure roll-up node (ADR-0016).
                own_current = own_here.get(account.id, {}).get("current", 0.0)
                rows.append(
                    {
                        "id": account.id,
                        "key": "%s|b%s" % (dpath, account.id),
                        "parent_key": (
                            "%s|b%s" % (dpath, pid) if pid in rolled else dpath
                        ),
                        "row_type": "account",
                        "account_id": account.id,
                        "dims": dims_map,
                        "code": account.code,
                        "name": account.name,
                        "level": lvl,
                        "has_children": bool(kids),
                        "own_current": own_current,
                        **self._value_columns(rolled[account.id]),
                        **(
                            self._usage_drill_pairs(
                                fold,
                                lambda acc_id, tup: project(tup) == prefix
                                and account.id
                                in self._ancestor_ids(acc_by_id[acc_id]),
                            )
                            if moved
                            else {}
                        ),
                    }
                )
                for child in kids:
                    emit_acc(child, lvl + 1)

            for root in roots:
                emit_acc(root, level)

        def emit_level(prefix, depth, level):
            info = pos[depth]
            # own-total per exact node at this position, for facts whose ancestor
            # path matches `prefix` exactly (exact-match nesting).
            own_total = defaultdict(lambda: dict.fromkeys(keys, 0.0))
            present = set()
            for (_a, tup), vals in own.items():
                if tup[:depth] != prefix:
                    continue
                node = tup[depth]
                tgt = own_total[node]
                for metric in keys:
                    tgt[metric] += vals[metric]
                if node:
                    present.add(node)
            # roll each exact node up over its analytic ancestors at this level
            rolled = defaultdict(lambda: dict.fromkeys(keys, 0.0))
            for node in present:
                for anc in info["paths"].get(node, [node]):
                    tgt = rolled[anc]
                    for metric in keys:
                        tgt[metric] += own_total[node][metric]
            node_set = set(rolled)
            roots = sorted(
                (nid for nid in node_set if info["parent"].get(nid) not in node_set),
                key=lambda nid: code_of(depth, nid),
            )

            # parent_key for the roots/sentinel at this level is the enclosing
            # dimension node (or False at the top); analytic children nest under
            # their own analytic parent (own_key), threaded through the recursion.
            base_parent = dim_key(prefix) if prefix else False

            def in_dim_row(tup, node_id):
                # the row's figure: exact prefix, value in node's subtree (or
                # untagged for the sentinel) at this level
                proj = project(tup)
                if proj[:depth] != prefix:
                    return False
                value = proj[depth]
                if not node_id:
                    return not value
                return bool(value) and node_id in ana_path.get(value, [value])

            def emit_node(node_id, lvl, parent_key):
                rec = info["rec"].get(node_id)
                child_nodes = sorted(
                    (c for c in info["children"].get(node_id, []) if c in node_set),
                    key=lambda nid: code_of(depth, nid),
                )
                exact_prefix = prefix + (node_id,)
                own_key = dim_key(exact_prefix)
                exact_has = exact_prefix in present_prefixes
                vals = rolled[node_id] if node_id else own_total[node_id]
                rows.append(
                    {
                        "id": False,
                        "key": own_key,
                        "parent_key": parent_key,
                        "row_type": "dim",
                        "dim_level": depth,
                        "dims": {
                            dims[i]: (exact_prefix[i] or False)
                            for i in range(depth + 1)
                        },
                        "code": rec.code if rec else "",
                        "name": rec.name if rec else "ไม่ระบุ",
                        "level": lvl,
                        "has_children": bool(child_nodes) or exact_has,
                        **self._value_columns(vals),
                        **(
                            self._usage_drill_pairs(
                                fold,
                                lambda _acc, tup: in_dim_row(tup, node_id),
                            )
                            if moved
                            else {}
                        ),
                    }
                )
                for child in child_nodes:
                    emit_node(child, lvl + 1, own_key)
                if exact_has:
                    if depth + 1 < n:
                        emit_level(exact_prefix, depth + 1, lvl + 1)
                    else:
                        emit_account_tree(exact_prefix, lvl + 1)

            for root in roots:
                emit_node(root, level, base_parent)
            if 0 in own_total:  # per-level untagged sentinel, shown last
                emit_node(0, level, base_parent)

        emit_level((), 0, 0)
        return rows

    def _fold_usage_to_pools(self, own, scope, acc_by_id, rounding):
        """Fold usage facts onto the tuple of the Budget Pool covering them.

        ``own`` maps ``(account_id, full_tuple)`` (``_DIM_FIELDS`` order, 0 =
        untagged) to the seven figures. A pool is a coordinate with non-zero own
        current. Usage at ``(account, tuple)`` moves to the tuple of the pool
        whose account is the usage account or an ancestor and whose every
        dimension is the usage value or an ancestor (untagged only matches
        untagged) — the engine's control node read on the dashboard's facts,
        deepest first for legacy nested pools. The usage keeps its own account,
        so the account tree under the pool tuple rolls it up to the pool's
        account. Usage no pool covers stays put (negative คงเหลือ: 0 available)
        unless it lies outside the filter ``scope``, where it was only fetched
        as a candidate for a covering pool, and is dropped.

        Returns ``{"own", "moved", "ana_path", "in_scope"}``; ``moved`` lists
        ``(account_id, source_tuple, target_tuple)`` for the drill-down pairs.
        """
        keys = self._FACT_KEYS
        full = self._DIM_FIELDS
        ids = {value for (_acc, tup) in own for value in tup if value}
        ana_path = {
            rec.id: self._ancestor_ids(rec) or [rec.id]
            for rec in self.env["account.analytic.account"].browse(list(ids))
        }
        pools = {
            key
            for key, vals in own.items()
            if not float_is_zero(vals["current"], precision_rounding=rounding)
        }
        positions = [(full.index(f), values) for f, values in scope.items()]

        def in_scope(tup):
            return all(
                tup[i] and set(values) & set(ana_path.get(tup[i], [tup[i]]))
                for i, values in positions
            )

        folded = {}
        moved = []
        for (acc_id, tup), vals in own.items():
            node = folded.setdefault((acc_id, tup), dict.fromkeys(keys, 0.0))
            for metric in keys:
                if metric not in self._USAGE_KEYS:
                    node[metric] += vals[metric]
            if not any(vals[metric] for metric in self._USAGE_KEYS):
                continue
            target = self._covering_pool_tuple(
                acc_id, tup, pools, acc_by_id, ana_path
            )
            if target is None:
                if not in_scope(tup):
                    continue
                target = tup
            node = folded.setdefault((acc_id, target), dict.fromkeys(keys, 0.0))
            for metric in self._USAGE_KEYS:
                node[metric] += vals[metric]
            if target != tup:
                moved.append((acc_id, tup, target))
        return {
            "own": {k: v for k, v in folded.items() if any(v.values())},
            "moved": moved,
            "ana_path": ana_path,
            "in_scope": in_scope,
        }

    def _covering_pool_tuple(self, acc_id, tup, pools, acc_by_id, ana_path):
        """Dimension tuple of the deepest pool covering ``(acc_id, tup)``."""
        account = acc_by_id.get(acc_id)
        acc_chain = self._ancestor_ids(account) if account else [acc_id]
        dim_chains = [
            list(enumerate(ana_path.get(value, [value]))) if value else [(0, 0)]
            for value in tup
        ]
        best, best_depth = None, -1
        for acc_depth, acc_node in enumerate(acc_chain):
            for combo in itertools.product(*dim_chains):
                candidate = tuple(value for _depth, value in combo)
                if (acc_node, candidate) not in pools:
                    continue
                depth = acc_depth + sum(d for d, _value in combo)
                if depth > best_depth:
                    best, best_depth = candidate, depth
        return best

    def _usage_drill_pairs(self, fold, in_row):
        """Coordinates a row's usage drill-down must add / remove (ADR-0016).

        The client drills a row by its dimensions + the filter; usage folded
        *into* the row from outside that scope is added (``usage_in``), usage
        inside the scope folded *out* to another row's pool is excluded
        (``usage_out``). ``in_row(account_id, full_tuple)`` is the row's figure
        predicate. Empty lists are omitted to keep the payload small.
        """
        full = self._DIM_FIELDS
        usage_in, usage_out = [], []
        for acc_id, src, tgt in fold["moved"]:
            src_in = in_row(acc_id, src) and fold["in_scope"](src)
            tgt_in = in_row(acc_id, tgt)
            if src_in == tgt_in:
                continue
            pair = {
                "account_id": acc_id,
                "dims": {f: (src[i] or False) for i, f in enumerate(full)},
            }
            (usage_in if tgt_in else usage_out).append(pair)
        out = {}
        if usage_in:
            out["usage_in"] = usage_in
        if usage_out:
            out["usage_out"] = usage_out
        return out

    def _facts_by_account_dims(self, model, domain, field, dims):
        """{(account_id, dim_tuple): Σ field} grouped by account + each dim.

        ``dim_tuple`` has one entry per field in ``dims`` (positional), with 0
        standing for an untagged value at that position.
        """
        out = {}
        for grp in self.env[model].read_group(
            domain, [field], ["account_id", *dims], lazy=False
        ):
            account = grp.get("account_id")
            if not account:
                continue
            tup = tuple((grp.get(d) or [0])[0] for d in dims)
            out[(account[0], tup)] = grp.get(field) or 0.0
        return out

    def _facts_by_account_dims_type(self, model, domain, field, dims):
        """{move_type: {(account_id, dim_tuple): Σ field}} for commitment lines."""
        out = {}
        for grp in self.env[model].read_group(
            domain, [field], ["account_id", *dims, "move_type"], lazy=False
        ):
            account = grp.get("account_id")
            move_type = grp.get("move_type")
            if not (account and move_type):
                continue
            tup = tuple((grp.get(d) or [0])[0] for d in dims)
            out.setdefault(move_type, {})[(account[0], tup)] = grp.get(field) or 0.0
        return out

    def _cap_facts_by_account_dims(self, commit_domain, dims):
        """{(account_id, dim_tuple): Σ cap} per active commitment.

        The cap *amount* and *account* come from the commitment header (matching
        the flat report). The dim *tuple* comes from the commitment's posted
        ``reserve`` line (stored fields, resolved set-based) so cap co-locates
        with reserved on the full tuple. A picker-created reservation pins one
        (activity, department, …) tuple; if some externally-created commitment
        ever has reserve lines spanning >1 tuple we log it and keep the last
        (the single-tuple invariant cannot be represented by one header cap).
        """
        commitments = self.env["budget.commitment"].search(commit_domain)
        if not commitments:
            return {}
        tup_of = {}
        multi = set()
        for grp in self.env["budget.commitment.line"].read_group(
            [
                ("commitment_id", "in", commitments.ids),
                ("state", "=", "posted"),
                ("move_type", "=", "reserve"),
            ],
            [],
            ["commitment_id", *dims],
            lazy=False,
        ):
            commitment = grp.get("commitment_id")
            if not commitment:
                continue
            cid = commitment[0]
            tup = tuple((grp.get(d) or [0])[0] for d in dims)
            if cid in tup_of:
                if tup_of[cid] != tup:
                    # Spans >1 tuple (no normal flow does this); pick a stable
                    # one so cap placement is deterministic, and log it.
                    multi.add(cid)
                    tup_of[cid] = min(tup_of[cid], tup)
            else:
                tup_of[cid] = tup
        if multi:
            _logger.warning(
                "budget.dashboard: %d commitment(s) have reserve lines spanning "
                "multiple %s tuples; cap placed on one tuple for those: %s",
                len(multi),
                dims,
                sorted(multi),
            )
        zero = tuple(0 for _ in dims)
        out = defaultdict(float)
        for commitment in commitments:
            out[(commitment.account_id.id, tup_of.get(commitment.id, zero))] += (
                commitment.amount
            )
        return out

    def _root_sort_key(self, account):
        """Top-level budget categories follow ``_ROOT_ORDER``, then code."""
        order = self._ROOT_ORDER
        code = account.code or ""
        return (order.index(code) if code in order else len(order), code)

    @api.model
    def get_reservation_grid(
        self,
        fiscal_year_id,
        filters=None,
        root_account_id=None,
        account_domain=None,
        breakdown=None,
    ):
        """Reservation picker feed: the full monitoring grid, made selectable.

        Reuses ``get_dashboard_data`` so the picker shows the **same columns**
        (งบต้นปี / งบปัจจุบัน / เงินจอง / คงเหลือ …) rolled up over the chosen
        ``filters`` dimension combination, then annotates each row with picker
        metadata:

        - ``budgetable`` — a real budget code, not a roll-up node;
        - ``cross_chargeable`` — may be pooled with others (ถัวจ่าย);
        - ``selectable`` — inside the host's own budget-account domain
          (``account_domain``, e.g. purchase.request's purchase_ok + product_id);
          defaults to ``budgetable`` when no domain is supplied.

        With ``breakdown`` set (a dim field or an ordered list of them, e.g.
        ``["activity_analytic_id", "department_analytic_id"]``) the grid is
        nested under those dimensions; the dimension group rows
        (``row_type == "dim"``) are display-only and never selectable — only
        budget-account rows can be picked.

        The displayed ``คงเหลือ`` is the rolled-up figure; the authoritative
        control-node availability (ADR 0005) is enforced by the engine at
        reserve time.
        """
        data = self.get_dashboard_data(
            fiscal_year_id, root_account_id, filters or {}, breakdown
        )
        rows = data.get("rows", [])
        rounding = self.env.company.currency_id.rounding or 0.01
        selectable_ids = None
        # Account ids that have at least one selectable *strict descendant* — a
        # coarse pool whose own account is out of the host domain can still be
        # narrowed down to a pickable child code (ADR-0016).
        has_sel_desc = set()
        if account_domain:
            selectable_ids = set(self.env["budget.account"].search(account_domain).ids)
            for acc in self.env["budget.account"].browse(list(selectable_ids)):
                for anc in self._ancestor_ids(acc)[:-1]:  # strict ancestors
                    has_sel_desc.add(anc)
        # Only account rows map to a budget.account; activity (breakdown) group
        # rows are display-only and can never be picked.
        accounts = {
            a.id: a
            for a in self.env["budget.account"].browse(
                [r["id"] for r in rows if r.get("row_type") == "account"]
            )
        }
        for row in rows:
            account = (
                accounts.get(row["id"]) if row.get("row_type") == "account" else None
            )
            budgetable = bool(account and account.budgetable)
            row["budgetable"] = budgetable
            row["cross_chargeable"] = bool(account and account.cross_chargeable)
            # A pool row = an account carrying its own posted appropriation at
            # this exact dimension tuple.
            is_pool = account is not None and not float_is_zero(
                row.get("own_current", 0.0), precision_rounding=rounding
            )
            in_domain = selectable_ids is not None and row["id"] in selectable_ids
            narrowable = is_pool and account.id in has_sel_desc
            # A pool whose own account is outside the host domain can only be used
            # by narrowing to a pickable descendant code.
            narrow_required = narrowable and not in_domain
            row["account_narrowable"] = narrowable
            row["narrow_required"] = narrow_required
            if selectable_ids is None:
                row["selectable"] = budgetable
            else:
                # narrow_required rows are kept selectable so the coarse pool is
                # not pruned away; the client blocks confirm until a descendant
                # code is chosen.
                row["selectable"] = in_domain or narrow_required
        # When the host constrains selectable codes (account_domain), show only
        # those codes and the dimension/roll-up rows leading to them — not every
        # code under the category. Domain-less hosts (budget.commitment) keep the
        # full grid.
        if selectable_ids is not None:
            rows = self._prune_to_selectable(rows)
        return {
            "rows": rows,
            "currency_id": data.get("currency_id"),
            "hier_op": data.get("hier_op", "="),
            "filter_ancestors": data.get("filter_ancestors", {}),
        }

    @api.model
    def _prune_to_selectable(self, rows):
        """Keep only selectable budget-account rows plus the ancestor rows that
        lead to them, so the reservation picker lists just the pickable
        รหัสงบประมาณ. A ส่วนงาน/กิจกรรม/กองทุน branch with nothing selectable falls
        away with its last child. Ancestry is walked through ``parent_key``."""
        by_key = {row["key"]: row for row in rows}
        keep = set()
        for row in rows:
            if not row.get("selectable"):
                continue
            keep.add(row["key"])
            pk = row.get("parent_key")
            while pk and pk not in keep:
                keep.add(pk)
                parent = by_key.get(pk)
                pk = parent.get("parent_key") if parent else False
        return [row for row in rows if row["key"] in keep]

    @api.model
    def get_selectable_roots(self, account_domain):
        """Root expense categories that contain at least one account matching
        ``account_domain``.

        The reservation picker scopes its ประเภทงบ dropdown to these, so a host
        never opens on — or switches to — a category with nothing selectable.
        Root resolution lives here, next to the dashboard's other ``parent_path``
        helpers, reusing :meth:`_root_category_map` rather than reparsing
        ``parent_path`` in the client.
        """
        if not account_domain:
            return []
        account_ids = self.env["budget.account"].search(account_domain).ids
        return list(set(self._root_category_map(account_ids).values()))

    @api.model
    def get_overview_departments(self):
        """Department (ส่วนงาน) options for the overview multi-select filter.

        Returns the top-level departments when the analytic tree is hierarchical
        (so a faculty stands in for all its sub-departments via ``child_of``);
        otherwise the full flat list. Mirrors the dashboard's hierarchy guard.
        """
        Analytic = self.env["account.analytic.account"]
        domain = [("root_plan_id.code", "=", "departments")]
        if "parent_id" in Analytic._fields:
            domain.append(("parent_id", "=", False))
        return Analytic.search_read(
            domain, ["id", "display_name", "code"], order="code"
        )

    @api.model
    def get_overview_data(self, fiscal_year_id, source_id=None, department_ids=None):
        """Landing-page payload: cards + sections + monthly trend + movements.

        Cards reuse ``get_dashboard_data`` and keep only the root rows
        (``level == 0``), so each category figure matches the detailed
        monitoring report exactly and a card can drill into it unchanged.
        ``department_ids`` (optional list) scopes every figure to those
        departments. ``sections`` are extension-contributed dimension tables
        (see :meth:`_overview_sections`); ``timeseries`` is the monthly usage
        trend. Recent movements are plain searches (never ``sudo``) so the
        global operating-unit record rules scope them to the current user.
        """
        currency_id = self.env.company.currency_id.id
        data = {
            "currency_id": currency_id,
            "cards": [],
            "totals": {},
            "recent": {},
            "sections": [],
            "timeseries": {},
            "hier_op": (
                "child_of"
                if "parent_id" in self.env["account.analytic.account"]._fields
                else "="
            ),
        }
        if not fiscal_year_id:
            return data

        filters = {}
        if source_id:
            filters["source_analytic_id"] = source_id
        if department_ids:
            filters["department_analytic_id"] = department_ids
        rows = self.get_dashboard_data(fiscal_year_id, None, filters)["rows"]
        cards = [row for row in rows if row["level"] == 0]

        totals = dict.fromkeys(self._OVERVIEW_KEYS, 0.0)
        for card in cards:
            for key in self._OVERVIEW_KEYS:
                totals[key] += card.get(key, 0.0)

        self._attach_breakdowns(cards, fiscal_year_id, source_id, department_ids)
        data["cards"] = cards
        data["totals"] = totals
        data["recent"] = self._recent_movements(fiscal_year_id)
        data["sections"] = self._overview_sections(
            fiscal_year_id, source_id, department_ids
        )
        data["timeseries"] = self._overview_timeseries(
            fiscal_year_id, source_id, department_ids
        )
        return data

    # ------------------------------------------------------------------
    # overview sections (open for extension) + monthly trend
    # ------------------------------------------------------------------
    def _overview_sections(self, fiscal_year_id, source_id, department_ids=None):
        """Extra dimension sections shown below the category cards.

        Budget core defines none. A module that owns an analytic dimension
        appends its section by overriding this method (``super()`` + append) —
        e.g. ``kmitl_project`` / ``procurement_plan`` — so the overview is open
        for extension without budget knowing those dimensions. Each section is
        ``{key, title, drill_dim, items}`` where every item is
        ``{id, code, name, current, used, remaining}`` (see
        :meth:`_dim_section_items`). The front end renders them generically.
        """
        return []

    def _department_leaf(self, department_ids):
        """Domain leaf scoping to a department set, hierarchy-aware (or None)."""
        if not department_ids:
            return None
        has_tree = "parent_id" in self.env["account.analytic.account"]._fields
        return (
            "department_analytic_id",
            "child_of" if has_tree else "in",
            department_ids,
        )

    def _dim_section_items(
        self, dim_field, fiscal_year_id, source_id, department_ids=None, limit=8
    ):
        """Per-node reservation figures for a reservation-based dimension.

        Projects (โครงการ/กิจกรรม) and procurement plans (แผนจัดซื้อจัดจ้าง)
        earmark a budget by **reserving** it, then spend it down by
        **consuming** it — they are not appropriated against their own
        dimension. So a section shows, per node:

            current   (งบ)      = Σ reserve  — the earmark
            used      (ใช้ไป)    = Σ consume  — เบิกจ่าย
            remaining (คงเหลือ)  = reserve − consume

        (mirrors each module's "Budget Remaining" definition). Grouped by the
        exact dimension account (one analytic account per project/plan), sorted
        by งบ desc, with the tail folded into an aggregated "อื่น ๆ" row so a
        section stays bounded. Honours the same source / department scope as the
        cards.
        """
        cl_dom = [
            ("state", "=", "posted"),
            ("commitment_id.state", "in", self._ACTIVE_COMMITMENT_STATES),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("move_type", "in", ("reserve", "consume")),
            (dim_field, "!=", False),
        ]
        if source_id:
            cl_dom.append(("source_analytic_id", "=", source_id))
        dep = self._department_leaf(department_ids)
        if dep:
            cl_dom.append(dep)

        current, used = defaultdict(float), defaultdict(float)
        for grp in self.env["budget.commitment.line"].read_group(
            cl_dom, ["amount"], [dim_field, "move_type"], lazy=False
        ):
            rec = grp.get(dim_field)
            move_type = grp.get("move_type")
            if not rec or not move_type:
                continue
            target = current if move_type == "reserve" else used
            target[rec[0]] += grp.get("amount") or 0.0

        ids = set(current) | set(used)
        if not ids:
            return []
        info = {
            a.id: (a.code, a.name)
            for a in self.env["account.analytic.account"].browse(list(ids))
        }
        items = []
        for analytic_id in ids:
            cur = current.get(analytic_id, 0.0)
            usd = used.get(analytic_id, 0.0)
            code, name = info.get(analytic_id, ("", ""))
            items.append(
                {
                    "id": analytic_id,
                    "code": code or "",
                    "name": name or "",
                    "current": cur,
                    "used": usd,
                    "remaining": cur - usd,
                }
            )
        items.sort(key=lambda x: (-x["current"], x["code"]))
        if len(items) > limit + 1:
            head, tail = items[:limit], items[limit:]
            items = head + [
                {
                    "id": False,
                    "code": "",
                    "name": "อื่น ๆ (%d)" % len(tail),
                    "current": sum(t["current"] for t in tail),
                    "used": sum(t["used"] for t in tail),
                    "remaining": sum(t["remaining"] for t in tail),
                }
            ]
        return items

    def _overview_timeseries(self, fiscal_year_id, source_id, department_ids=None):
        """Monthly จอง / ผูกพัน / เบิกจ่าย flow across the fiscal year.

        Raw ``Σ amount`` of posted reserve/obligate/consume commitment lines,
        bucketed by month over the whole fiscal-year span (empty months kept so
        the x-axis is continuous). Same source / department scope as the cards.
        """
        fy = self.env["account.fiscal.year"].browse(fiscal_year_id)
        if not fy.exists() or not fy.date_from or not fy.date_to:
            return {}
        months, labels = [], []
        year, month = fy.date_from.year, fy.date_from.month
        end = (fy.date_to.year, fy.date_to.month)
        while (year, month) <= end:
            months.append("%04d-%02d" % (year, month))
            labels.append(
                "%s %02d" % (self._THAI_MONTH_ABBR[month - 1], (year + 543) % 100)
            )
            month += 1
            if month > 12:
                month, year = 1, year + 1
        index = {mk: i for i, mk in enumerate(months)}
        series = {mt: [0.0] * len(months) for mt in self._TS_MOVE_TYPES}

        cl_dom = [
            ("state", "=", "posted"),
            ("commitment_id.state", "in", self._ACTIVE_COMMITMENT_STATES),
            ("account_fiscal_year_id", "=", fiscal_year_id),
        ]
        if source_id:
            cl_dom.append(("source_analytic_id", "=", source_id))
        dep = self._department_leaf(department_ids)
        if dep:
            cl_dom.append(dep)
        for grp in self.env["budget.commitment.line"].read_group(
            cl_dom, ["amount"], ["date:month", "move_type"], lazy=False
        ):
            move_type = grp.get("move_type")
            rng = (grp.get("__range") or {}).get("date:month") or {}
            start = rng.get("from")
            if move_type not in series or not start:
                continue
            i = index.get(start[:7])
            if i is not None:
                series[move_type][i] = grp.get("amount") or 0.0
        # Convert raw monthly flows to cumulative running balances, then net them
        # so ผูกพัน drops to 0 once เบิกจ่าย is posted (even in a later month).
        n = len(months)
        r_cum, o_cum, c_cum = [0.0] * n, [0.0] * n, [0.0] * n
        for i in range(n):
            prev = i - 1
            r_cum[i] = (r_cum[prev] if i > 0 else 0.0) + series["reserve"][i]
            o_cum[i] = (o_cum[prev] if i > 0 else 0.0) + series["obligate"][i]
            c_cum[i] = (c_cum[prev] if i > 0 else 0.0) + series["consume"][i]
        return {
            "labels": labels,
            "reserve": [max(0.0, r_cum[i] - o_cum[i]) for i in range(n)],
            "obligate": [max(0.0, o_cum[i] - c_cum[i]) for i in range(n)],
            "consume": list(c_cum),
        }

    def _recent_movements(self, fiscal_year_id):
        """Latest documents of each type for the selected fiscal year.

        Scoped by fiscal year so the feed matches the cards; every header
        model stores ``account_fiscal_year_id``. Source is deliberately NOT
        applied here: it is a line-level dimension (the cards sum it from
        lines), and transfer-generated moves carry no header source, so a
        header-level source filter would silently drop real documents. Each
        model's ``_order`` is already ``date desc``.
        """
        limit = self._RECENT_LIMIT
        domain = [("account_fiscal_year_id", "=", fiscal_year_id)]

        def fmt(value):
            return format_date(self.env, value) if value else ""

        commitments = self.env["budget.commitment"].search(domain, limit=limit)
        moves = self.env["budget.move"].search(domain, limit=limit)
        # budget.transfer lives in the optional `budget_transfer` add-on
        # (ADR-0013); the core dashboard stays self-contained without it.
        transfers = (
            self.env["budget.transfer"].search(domain, limit=limit)
            if "budget.transfer" in self.env
            else []
        )
        return {
            "commitment": [
                {
                    "id": c.id,
                    "name": c.name,
                    "date": fmt(c.date),
                    "amount": c.amount,
                    "state": c.state,
                }
                for c in commitments
            ],
            "move": [
                {
                    "id": m.id,
                    "name": m.name,
                    "date": fmt(m.date),
                    "amount": m.total_amount,
                    "move_type": m.move_type,
                    "state": m.state,
                }
                for m in moves
            ],
            "transfer": [
                {
                    "id": t.id,
                    "name": t.name,
                    "date": fmt(t.date),
                    "amount": t.amount,
                    "state": t.state,
                }
                for t in transfers
            ],
        }

    def _attach_breakdowns(self, cards, fiscal_year_id, source_id, department_ids=None):
        """Attach top-level fund & activity breakdowns to each category card.

        For every root category we show how its current budget (a) and usage
        (e = Σreserve) split across the first-level funds and activities, so a
        card gives an at-a-glance picture of where the budget sits. Figures
        reuse the card's own definitions (remaining = current - used).
        """
        if not cards:
            return
        card_ids = {c["id"] for c in cards}
        for dim, attr in (
            ("fund_analytic_id", "funds"),
            ("activity_analytic_id", "activities"),
        ):
            breakdown = self._dim_breakdown(
                dim, fiscal_year_id, source_id, card_ids, department_ids
            )
            for card in cards:
                card[attr] = breakdown.get(card["id"], [])

    def _dim_breakdown(
        self, dim, fiscal_year_id, source_id, card_ids, department_ids=None
    ):
        """Per-root breakdown over the top-level nodes of one analytic dim.

        current comes from posted appropriation/entry move lines; used is the
        net reservation (``move_type == 'reserve'`` on active commitments).
        Both the budget account and the dimension value are rolled up to their
        respective roots (``parent_path[0]``) before accumulation.
        """
        move_dom = [
            ("parent_state", "=", "posted"),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("move_type", "in", ("appropriation", "entry")),
        ]
        cl_dom = [
            ("state", "=", "posted"),
            ("commitment_id.state", "in", self._ACTIVE_COMMITMENT_STATES),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("move_type", "=", "reserve"),
        ]
        if source_id:
            move_dom.append(("source_analytic_id", "=", source_id))
            cl_dom.append(("source_analytic_id", "=", source_id))
        dep = self._department_leaf(department_ids)
        if dep:
            move_dom.append(dep)
            cl_dom.append(dep)

        cur_groups = self.env["budget.move.line"].read_group(
            move_dom, ["balance"], ["account_id", dim], lazy=False
        )
        used_groups = self.env["budget.commitment.line"].read_group(
            cl_dom, ["amount"], ["account_id", dim], lazy=False
        )

        all_groups = cur_groups + used_groups
        root_of = self._root_category_map(
            {g["account_id"][0] for g in all_groups if g.get("account_id")}
        )
        top_of = self._top_level_map({g[dim][0] for g in all_groups if g.get(dim)})

        current = defaultdict(lambda: defaultdict(float))
        used = defaultdict(lambda: defaultdict(float))
        for groups, field, target in (
            (cur_groups, "balance", current),
            (used_groups, "amount", used),
        ):
            for grp in groups:
                acc = grp.get("account_id")
                if not acc:
                    continue
                root = root_of.get(acc[0])
                if root not in card_ids:
                    continue
                dval = grp.get(dim)
                # untagged lines bucket under id 0 ("ไม่ระบุ") so the rows
                # still reconcile with the card total.
                top = top_of.get(dval[0], dval[0]) if dval else 0
                target[root][top] += grp.get(field) or 0.0

        top_ids = {
            tid
            for buckets in (current, used)
            for d in buckets.values()
            for tid in d
            if tid
        }
        info = {
            a.id: (a.code, a.name)
            for a in self.env["account.analytic.account"].browse(list(top_ids))
        }
        info[0] = ("", "ไม่ระบุ")

        result = {}
        for root in set(current) | set(used):
            items = []
            for tid in set(current[root]) | set(used[root]):
                cur = current[root].get(tid, 0.0)
                usd = used[root].get(tid, 0.0)
                code, name = info.get(tid, ("", ""))
                items.append(
                    {
                        "id": tid,
                        "code": code,
                        "name": name,
                        "current": cur,
                        "used": usd,
                        "remaining": cur - usd,
                    }
                )
            items.sort(key=lambda x: (-x["current"], x["code"]))
            result[root] = items
        return result

    def _root_category_map(self, account_ids):
        """budget.account id -> its root category id (parent_path[0])."""
        out = {}
        for acc in self.env["budget.account"].browse(list(account_ids)):
            ids = self._ancestor_ids(acc)
            out[acc.id] = ids[0] if ids else acc.id
        return out

    def _top_level_map(self, analytic_ids):
        """analytic account id -> its top-level ancestor id (parent_path[0])."""
        out = {}
        for rec in self.env["account.analytic.account"].browse(list(analytic_ids)):
            path = (rec.parent_path or "").strip("/").split("/")
            out[rec.id] = int(path[0]) if path and path[0] else rec.id
        return out

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _value_columns(r):
        """Map the seven rolled-up sources to the ten displayed money columns."""
        reserved_v, obligated_v, consumed_v, current_v = (
            r["reserved"],
            r["obligated"],
            r["consumed"],
            r["current"],
        )
        return {
            "initial": r["initial"],
            "adjustment": current_v - r["initial"],
            "current": current_v,
            "cap": r["cap"],
            "reserved": reserved_v - obligated_v,  # b
            "obligated": obligated_v - consumed_v,  # c
            "consumed": consumed_v,  # d
            "used": reserved_v,  # e = b + c + d (net of returns)
            "remaining": current_v - reserved_v,  # f
            "returned": -r.get("returned", 0.0),  # g ส่งคืนเงินเหลือจ่าย (shown positive)
        }

    def _make_row(self, account, r, level, has_children):
        # ``key``/``parent_key`` drive the front-end tree (collapse + indent).
        # A plain budget.account id is unique here, so the key is just ``b<id>``;
        # the breakdown view qualifies it with the dimension (see _breakdown_rows).
        pid = account.parent_id.id
        return {
            "id": account.id,
            "key": "b%s" % account.id,
            "parent_key": "b%s" % pid if pid else False,
            "row_type": "account",
            "account_id": account.id,
            "code": account.code,
            "name": account.name,
            "level": level,
            "has_children": has_children,
            **self._value_columns(r),
        }

    def _dashboard_accounts(self, root_account_id):
        Account = self.env["budget.account"]
        domain = [("budget_type", "=", "expense")]
        if root_account_id:
            root = Account.browse(root_account_id)
            if root.exists():
                domain.append(("parent_path", "=like", (root.parent_path or "") + "%"))
        return Account.search(domain, order="code")

    @staticmethod
    def _ancestor_ids(account):
        """ids along parent_path, root-first, including the account itself."""
        return [int(x) for x in (account.parent_path or "").strip("/").split("/") if x]

