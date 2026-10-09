from odoo import models


class BudgetController(models.AbstractModel):
    """Available = Σ balance of every posted ledger line at the control node.

    Reservations, obligations and consumptions are posted to the ledger
    (ADR-0016), so "current − used" collapses into one sum: nothing is read
    from ``budget.commitment.line`` any more. The pool tags are pinned on every
    bucket alike (Q3), which retires the usage-side ``include_pool_tags=False``.
    """

    _inherit = "budget.controller"

    def _absent_dim_leaves(self, dims, include_pool_tags=True):
        return super()._absent_dim_leaves(dims, include_pool_tags=True)

    def _sum_current(self, controls, dims, fiscal_year_id, company_id):
        """Σ posted balance of every bucket over the control-node subtree."""
        domain = [
            ("parent_state", "=", "posted"),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("company_id", "=", company_id),
        ] + self._control_scope(controls, dims)
        groups = self.env["budget.move.line"].read_group(domain, ["balance"], [])
        return (groups[0].get("balance") or 0.0) if groups else 0.0

    def _sum_used(self, controls, dims, fiscal_year_id, company_id):
        # Already netted into _sum_current by the ledger postings.
        return 0.0
