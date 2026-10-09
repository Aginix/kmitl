from odoo import models

_BUCKETS = ("reserve", "obligate", "consume")


class BudgetDashboard(models.AbstractModel):
    """Dashboard usage read from the budget ledger (ADR-0016).

    Each band is the negated Σ balance of its bucket: b = reserve,
    c = obligate, d = consume. They are folded back into the cumulative figures
    the dashboard expects (reserve ⊇ obligate ⊇ consume).
    """

    _inherit = "budget.dashboard"

    def _usage_base_domain(self):
        return [("parent_state", "=", "posted"), ("commitment_id", "!=", False)]

    def _usage_read_group(self, domain, groupby):
        buckets = {}
        for grp in self.env["budget.move.line"].read_group(
            self._usage_base_domain() + list(domain),
            ["balance"],
            list(groupby) + ["move_type", "is_return"],
            lazy=False,
        ):
            sums = buckets.setdefault(
                self._usage_group_key(grp, groupby),
                dict.fromkeys(_BUCKETS + ("returned",), 0.0),
            )
            balance = grp.get("balance") or 0.0
            if grp.get("move_type") in _BUCKETS:
                sums[grp["move_type"]] += balance
            if grp.get("is_return"):
                sums["returned"] += balance
        return {
            key: {
                "reserve": -(sums["reserve"] + sums["obligate"] + sums["consume"]),
                "obligate": -(sums["obligate"] + sums["consume"]),
                "consume": -sums["consume"],
                # คืนจอง posts reserve +X; the figure stays signed negative.
                "returned": -sums["returned"],
            }
            for key, sums in buckets.items()
        }

    def _usage_commitment_ids(self, domain):
        groups = self.env["budget.move.line"].read_group(
            self._usage_base_domain() + list(domain),
            ["commitment_id"],
            ["commitment_id"],
        )
        return [grp["commitment_id"][0] for grp in groups if grp.get("commitment_id")]
