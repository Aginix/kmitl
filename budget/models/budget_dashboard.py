import logging

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
        dim_leaves = [
            (fname, "=", filters[fname])
            for fname in self._DIM_FIELDS
            if filters.get(fname)
        ]

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

        child_count = {}
        for acc in accounts:
            pid = acc.parent_id.id
            if pid in rolled:
                child_count[pid] = child_count.get(pid, 0) + 1

        rows = []
        for acc in accounts:
            r = rolled[acc.id]
            res_v, obl_v, con_v, cur_v = (
                r["reserved"],
                r["obligated"],
                r["consumed"],
                r["current"],
            )
            in_scope_ancestors = [a for a in self._ancestor_ids(acc) if a in rolled]
            rows.append(
                {
                    "id": acc.id,
                    "code": acc.code,
                    "name": acc.name,
                    "parent_id": acc.parent_id.id if acc.parent_id.id in rolled else False,
                    "level": max(0, len(in_scope_ancestors) - 1),
                    "has_children": child_count.get(acc.id, 0) > 0,
                    "initial": r["initial"],
                    "adjustment": cur_v - r["initial"],
                    "current": cur_v,
                    "cap": r["cap"],
                    "reserved": res_v - obl_v,  # b
                    "obligated": obl_v - con_v,  # c
                    "consumed": con_v,  # d
                    "used": res_v,  # e = b + c + d
                    "remaining": cur_v - res_v,  # f
                }
            )
        return {"rows": rows, "currency_id": currency_id}

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
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
