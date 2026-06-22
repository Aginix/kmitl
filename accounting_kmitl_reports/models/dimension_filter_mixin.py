# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models

# Dimension plan codes the KMITL reports can filter on. Order is the display
# order. Read from each move line's ``analytic_distribution`` (a JSON of
# {analytic_account_id: percentage}).
DIMENSION_CODES = ("departments", "sources", "funds", "activities")
# Hierarchical dimensions: a selected node also matches all of its descendants
# (when analytic accounts carry a ``parent_id`` hierarchy). ``sources`` is flat.
HIERARCHICAL_DIMS = ("departments", "funds", "activities")


class DimensionFilterMixin(models.AbstractModel):
    """Shared KMITL accounting-dimension filtering for the report models.

    Turns the dimension values selected on screen into ``analytic_distribution``
    domain leaves so reports can restrict the ledger to specific KMITL
    dimensions. Used by the Trial Balance and the Aged Partner Balance reports.
    """

    _name = "accounting_kmitl_reports.dimension.filter.mixin"
    _description = "KMITL Report Dimension Filter Mixin"

    @api.model
    def _kmitl_build_dim_leaves(self, dims):
        """Turn the selected dimension values into ``analytic_distribution``
        domain leaves. Within a dimension the ids (plus descendants for
        hierarchical dimensions) are OR-ed; the resulting leaves are AND-ed
        across dimensions by the domain builder.
        """
        analytic = self.env["account.analytic.account"]
        use_child = "parent_id" in analytic._fields
        leaves = []
        for code in DIMENSION_CODES:
            ids = (dims or {}).get(code) or []
            if not ids:
                continue
            if code in HIERARCHICAL_DIMS and use_child:
                ids = analytic.search([("id", "child_of", ids)]).ids
            leaves.append(("analytic_distribution", "in", ids))
        return leaves
