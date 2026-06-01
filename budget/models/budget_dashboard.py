import logging
from collections import defaultdict

from odoo import api, models

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
