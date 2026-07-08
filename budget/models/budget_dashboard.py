import logging
from collections import defaultdict

from odoo import api, models
from odoo.tools import format_date

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
        "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
        "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
    )

    @api.model
    def get_dashboard_data(
        self, fiscal_year_id, root_account_id=None, filters=None, breakdown=None
    ):
        """Return ``{"rows": [...], "currency_id": id}`` for the dashboard grid.

        ``breakdown`` (optional) is an analytic dimension field name, or an
        ordered list of them (e.g. ``["activity_analytic_id",
        "department_analytic_id"]``). When set, the budget-account tree is
        nested under those dimensions' hierarchies (outer to inner) — same
        columns, same roll-up — instead of being the sole row axis. See
        :meth:`_breakdown_rows`.
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
        dim_leaves = []
        for fname in self._DIM_FIELDS:
            val = filters.get(fname)
            if not val:
                continue
            is_list = isinstance(val, (list, tuple))
            # source is flat (exact / "in"); the hierarchical dims use child_of
            # when the analytic tree exists, else exact / "in" for a value list.
            if fname == "source_analytic_id":
                op = "in" if is_list else "="
            elif is_list:
                op = "child_of" if hier_op == "child_of" else "in"
            else:
                op = hier_op
            dim_leaves.append((fname, op, val))

        # Shared base domains for every column; dim filters apply set-based.
        move_base = [
            ("parent_state", "=", "posted"),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("account_id", "in", account_ids),
        ] + dim_leaves
        cl_base = [
            ("state", "=", "posted"),
            ("commitment_id.state", "in", self._ACTIVE_COMMITMENT_STATES),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("account_id", "in", account_ids),
        ] + dim_leaves
        # (3) approved cap = Σ active commitment caps. Header analytic dims are
        # non-stored, so when a dimension filter is set the matching commitments
        # are resolved through their stored lines.
        commit_domain = [
            ("state", "in", self._ACTIVE_COMMITMENT_STATES),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("account_id", "in", account_ids),
        ]
        if dim_leaves:
            match = self.env["budget.commitment.line"].search(cl_base).mapped(
                "commitment_id"
            )
            commit_domain.append(("id", "in", match.ids))

        # Optional breakdown: nest the budget-account tree under one or more
        # analytic dimensions (ordered, e.g. activities then departments)
        # instead of using the account tree as the sole row axis.
        dims = self._normalize_breakdown(breakdown)
        if dims:
            rows = self._breakdown_rows(
                dims, accounts, account_ids, move_base, cl_base, commit_domain
            )
            return {"rows": rows, "currency_id": currency_id, "hier_op": hier_op}

        # --- (a) current pool and (1) initial, from posted move lines ---
        current = self._sum_by_account(
            "budget.move.line",
            move_base + [("move_type", "in", ("appropriation", "entry"))],
            "balance",
        )
        initial = self._sum_by_account(
            "budget.move.line",
            move_base
            + [
                ("move_type", "=", "appropriation"),
                ("appropriation_type", "=", "initial"),
            ],
            "balance",
        )

        # --- b/c/d from posted commitment lines of active commitments ---
        by_type = self._sum_by_account_and_type(
            "budget.commitment.line", cl_base, "amount"
        )
        reserved = by_type.get("reserve", {})
        obligated = by_type.get("obligate", {})
        consumed = by_type.get("consume", {})
        # (g) ส่งคืนเงินเหลือจ่าย: the คืนจอง lines (negative reserve, is_return),
        # summed separately as a memo column. The signed reserve bucket above
        # already nets these in, so b/e/f need no change — they drop/rise on
        # their own once a return is posted.
        returned = self._sum_by_account(
            "budget.commitment.line", cl_base + [("is_return", "=", True)], "amount"
        )

        cap = self._sum_by_account("budget.commitment", commit_domain, "amount")

        # --- roll own values up the subtree via parent_path ---
        keys = (
            "initial",
            "current",
            "cap",
            "reserved",
            "obligated",
            "consumed",
            "returned",
        )
        sources = {
            "initial": initial,
            "current": current,
            "cap": cap,
            "reserved": reserved,
            "obligated": obligated,
            "consumed": consumed,
            "returned": returned,
        }
        rolled = {aid: dict.fromkeys(keys, 0.0) for aid in account_ids}
        for acc in accounts:
            own = {k: sources[k].get(acc.id, 0.0) for k in keys}
            if not any(own.values()):
                continue
            for aid in self._ancestor_ids(acc):
                node = rolled.get(aid)
                if node is not None:
                    for k in keys:
                        node[k] += own[k]

        # Emit rows in depth-first pre-order built from parent_id. Ordering by
        # code alone is NOT a valid tree order (a deep child can sort before its
        # parent), which is what made the collapse/indentation render wrong.
        acc_by_id = {acc.id: acc for acc in accounts}
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
            rows.append(self._make_row(acc, rolled[acc.id], level, bool(kids)))
            for child in reversed(kids):
                stack.append((child, level + 1))
        return {"rows": rows, "currency_id": currency_id, "hier_op": hier_op}

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

    def _breakdown_rows(
        self, dims, accounts, account_ids, move_base, cl_base, commit_domain
    ):
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
        """
        keys = (
            "initial",
            "current",
            "cap",
            "reserved",
            "obligated",
            "consumed",
            "returned",
        )

        sources = {
            "current": self._facts_by_account_dims(
                "budget.move.line",
                move_base + [("move_type", "in", ("appropriation", "entry"))],
                "balance",
                dims,
            ),
            "initial": self._facts_by_account_dims(
                "budget.move.line",
                move_base
                + [
                    ("move_type", "=", "appropriation"),
                    ("appropriation_type", "=", "initial"),
                ],
                "balance",
                dims,
            ),
            "cap": self._cap_facts_by_account_dims(commit_domain, dims),
        }
        by_type = self._facts_by_account_dims_type(
            "budget.commitment.line", cl_base, "amount", dims
        )
        sources["reserved"] = by_type.get("reserve", {})
        sources["obligated"] = by_type.get("obligate", {})
        sources["consumed"] = by_type.get("consume", {})
        # (g) ส่งคืนเงินเหลือจ่าย: คืนจอง lines (negative reserve, is_return).
        sources["returned"] = self._facts_by_account_dims(
            "budget.commitment.line",
            cl_base + [("is_return", "=", True)],
            "amount",
            dims,
        )

        # own[(account_id, dim_tuple)] = {metric: value}; 0 in a tuple = untagged
        # at that position. Each read_group group maps to exactly one tuple, so
        # money is never double-counted and Σ over tuples == the flat report.
        own = {}
        for metric in keys:
            for (acc_id, tup), val in sources[metric].items():
                own.setdefault(
                    (acc_id, tup), dict.fromkeys(keys, 0.0)
                )[metric] = val
        # Index by full tuple so emit_account_tree need not rescan all facts.
        own_by_tuple = defaultdict(dict)
        for (acc_id, tup), vals in own.items():
            own_by_tuple[tup][acc_id] = vals

        acc_by_id = {a.id: a for a in accounts}
        account_id_set = set(account_ids)
        Analytic = self.env["account.analytic.account"]
        n = len(dims)

        # Full tuples and every prefix present, for O(1) "has deeper content".
        present_prefixes = {
            tup[:k] for (_a, tup) in own for k in range(1, n + 1)
        }

        # Per-position analytic hierarchy (paths/parent/children/rec) over the
        # dim values that actually appear at that position (+ their ancestors).
        present_by_pos = [set() for _ in range(n)]
        for (_a, tup) in own:
            for i, value in enumerate(tup):
                if value:
                    present_by_pos[i].add(value)
        pos = []
        for present_ids in present_by_pos:
            paths = {}
            union = set()
            for rec in Analytic.browse(list(present_ids)):
                path = [
                    int(x)
                    for x in (rec.parent_path or "").strip("/").split("/")
                    if x
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
                (children[pid] if pid in rolled else roots).append(
                    acc_by_id[acc_id]
                )
            roots.sort(key=self._root_sort_key)
            for kids in children.values():
                kids.sort(key=lambda a: a.code or "")
            dpath = dim_key(prefix)
            dims_map = {dims[i]: (prefix[i] or False) for i in range(n)}

            def emit_acc(account, lvl):
                kids = children.get(account.id, [])
                pid = account.parent_id.id
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
                        **self._value_columns(rolled[account.id]),
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
            out[
                (commitment.account_id.id, tup_of.get(commitment.id, zero))
            ] += commitment.amount
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
        selectable_ids = None
        if account_domain:
            selectable_ids = set(
                self.env["budget.account"].search(account_domain).ids
            )
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
            row["selectable"] = (
                budgetable
                if selectable_ids is None
                else account is not None and row["id"] in selectable_ids
            )
        return {
            "rows": rows,
            "currency_id": data.get("currency_id"),
            "hier_op": data.get("hier_op", "="),
        }

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
        return ("department_analytic_id", "child_of" if has_tree else "in", department_ids)

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
        return {
            "labels": labels,
            "reserve": series["reserve"],
            "obligate": series["obligate"],
            "consume": series["consume"],
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
        transfers = self.env["budget.transfer"].search(domain, limit=limit)
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

    def _attach_breakdowns(
        self, cards, fiscal_year_id, source_id, department_ids=None
    ):
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
        top_of = self._top_level_map(
            {g[dim][0] for g in all_groups if g.get(dim)}
        )

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
            tid for buckets in (current, used) for d in buckets.values() for tid in d if tid
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
                domain.append(
                    ("parent_path", "=like", (root.parent_path or "") + "%")
                )
        return Account.search(domain, order="code")

    @staticmethod
    def _ancestor_ids(account):
        """ids along parent_path, root-first, including the account itself."""
        return [
            int(x) for x in (account.parent_path or "").strip("/").split("/") if x
        ]

    def _sum_by_account(self, model, domain, field):
        result = {}
        for grp in self.env[model].read_group(domain, [field], ["account_id"]):
            account = grp.get("account_id")
            if account:
                result[account[0]] = grp.get(field) or 0.0
        return result

    def _sum_by_account_and_type(self, model, domain, field):
        out = {}
        groups = self.env[model].read_group(
            domain, [field], ["account_id", "move_type"], lazy=False
        )
        for grp in groups:
            account = grp.get("account_id")
            move_type = grp.get("move_type")
            if account and move_type:
                out.setdefault(move_type, {})[account[0]] = grp.get(field) or 0.0
        return out
