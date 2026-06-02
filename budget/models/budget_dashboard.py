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
        used       (e) รวม              b + c + d  (= Σreserve)
        remaining  (f) คงเหลือ           current - used
    """

    _name = "budget.dashboard"
    _description = "Budget Monitoring Dashboard"

    _DIM_FIELDS = (
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    )
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

    @api.model
    def get_dashboard_data(self, fiscal_year_id, root_account_id=None, filters=None):
        """Return ``{"rows": [...], "currency_id": id}`` for the dashboard grid."""
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
            if filters.get(fname):
                op = "=" if fname == "source_analytic_id" else hier_op
                dim_leaves.append((fname, op, filters[fname]))

        # --- (a) current pool and (1) initial, from posted move lines ---
        move_base = [
            ("parent_state", "=", "posted"),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("account_id", "in", account_ids),
        ] + dim_leaves
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
        cl_base = [
            ("state", "=", "posted"),
            ("commitment_id.state", "in", self._ACTIVE_COMMITMENT_STATES),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("account_id", "in", account_ids),
        ] + dim_leaves
        by_type = self._sum_by_account_and_type(
            "budget.commitment.line", cl_base, "amount"
        )
        reserved = by_type.get("reserve", {})
        obligated = by_type.get("obligate", {})
        consumed = by_type.get("consume", {})

        # --- (3) approved cap = Σ active commitment caps ---
        # Header analytic dims are non-stored, so when a dimension filter is set
        # the matching commitments are resolved through their stored lines.
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
        cap = self._sum_by_account("budget.commitment", commit_domain, "amount")

        # --- roll own values up the subtree via parent_path ---
        keys = ("initial", "current", "cap", "reserved", "obligated", "consumed")
        sources = {
            "initial": initial,
            "current": current,
            "cap": cap,
            "reserved": reserved,
            "obligated": obligated,
            "consumed": consumed,
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

    @api.model
    def get_reservation_grid(
        self, fiscal_year_id, analytic_distribution, root_account_id=None
    ):
        """Expense ``budget.account`` hierarchy with the control-node
        ``available`` per budgetable row, for a **fixed** dimension combination.

        Feeds the reservation picker widget: unlike ``get_dashboard_data`` (which
        rolls the tree up and treats dimensions as ``child_of`` filters), this
        evaluates ``budget.controller.get_available`` for the *exact*
        combination at each budgetable node — so the figure shown is the figure
        the reservation check will enforce (WYSIWYG). Non-budgetable rows are
        display-only (``available`` is ``None``).
        """
        currency_id = self.env.company.currency_id.id
        if not fiscal_year_id:
            return {"rows": [], "currency_id": currency_id}
        accounts = self._dashboard_accounts(root_account_id)
        if not accounts:
            return {"rows": [], "currency_id": currency_id}

        acc_by_id = {acc.id: acc for acc in accounts}
        children = defaultdict(list)
        roots = []
        for acc in accounts:
            if acc.parent_id.id in acc_by_id:
                children[acc.parent_id.id].append(acc)
            else:
                roots.append(acc)
        order = self._ROOT_ORDER
        roots.sort(
            key=lambda a: (
                order.index(a.code) if a.code in order else len(order),
                a.code,
            )
        )

        controller = self.env["budget.controller"]
        rows = []
        stack = [(acc, 0) for acc in reversed(roots)]
        while stack:
            acc, level = stack.pop()
            kids = children.get(acc.id, [])
            available = (
                controller.get_available(
                    acc, analytic_distribution, fiscal_year_id
                )
                if acc.budgetable
                else None
            )
            rows.append(
                {
                    "id": acc.id,
                    "code": acc.code,
                    "name": acc.name,
                    "parent_id": acc.parent_id.id,
                    "level": level,
                    "has_children": bool(kids),
                    "budgetable": acc.budgetable,
                    "cross_chargeable": acc.cross_chargeable,
                    "available": available,
                }
            )
            for child in reversed(kids):
                stack.append((child, level + 1))
        return {"rows": rows, "currency_id": currency_id}

    @api.model
    def get_overview_data(self, fiscal_year_id, source_id=None):
        """Landing-page payload: per-category cards + recent movements.

        Cards reuse ``get_dashboard_data`` and keep only the root rows
        (``level == 0``), so each category figure matches the detailed
        monitoring report exactly and a card can drill into it unchanged.
        Recent movements are plain searches (never ``sudo``) so the global
        operating-unit record rules scope them to the current user.
        """
        currency_id = self.env.company.currency_id.id
        data = {"currency_id": currency_id, "cards": [], "totals": {}, "recent": {}}
        if not fiscal_year_id:
            return data

        filters = {"source_analytic_id": source_id} if source_id else {}
        rows = self.get_dashboard_data(fiscal_year_id, None, filters)["rows"]
        cards = [row for row in rows if row["level"] == 0]

        totals = dict.fromkeys(self._OVERVIEW_KEYS, 0.0)
        for card in cards:
            for key in self._OVERVIEW_KEYS:
                totals[key] += card.get(key, 0.0)

        self._attach_breakdowns(cards, fiscal_year_id, source_id)
        data["cards"] = cards
        data["totals"] = totals
        data["recent"] = self._recent_movements(fiscal_year_id)
        return data

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

    def _attach_breakdowns(self, cards, fiscal_year_id, source_id):
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
            breakdown = self._dim_breakdown(dim, fiscal_year_id, source_id, card_ids)
            for card in cards:
                card[attr] = breakdown.get(card["id"], [])

    def _dim_breakdown(self, dim, fiscal_year_id, source_id, card_ids):
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
    def _make_row(self, account, r, level, has_children):
        reserved_v, obligated_v, consumed_v, current_v = (
            r["reserved"],
            r["obligated"],
            r["consumed"],
            r["current"],
        )
        return {
            "id": account.id,
            "code": account.code,
            "name": account.name,
            "parent_id": account.parent_id.id,
            "level": level,
            "has_children": has_children,
            "initial": r["initial"],
            "adjustment": current_v - r["initial"],
            "current": current_v,
            "cap": r["cap"],
            "reserved": reserved_v - obligated_v,  # b
            "obligated": obligated_v - consumed_v,  # c
            "consumed": consumed_v,  # d
            "used": reserved_v,  # e = b + c + d
            "remaining": current_v - reserved_v,  # f
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
