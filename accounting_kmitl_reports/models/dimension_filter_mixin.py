# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.tools import date_utils

# Dimension plan codes the KMITL reports can filter on. Order is the display
# order. Read from each move line's ``analytic_distribution`` (a JSON of
# {analytic_account_id: percentage}).
DIMENSION_CODES = ("departments", "sources", "funds", "activities")
# Display order of the dimension chips shown in the shared expand-detail panel.
DETAIL_DIM_PLANS = ("funds", "departments", "activities", "sources")
# Lines never shown in the detail panel.
_SKIP_DISPLAY_TYPES = ["line_section", "line_note"]


class DimensionFilterMixin(models.AbstractModel):
    """Shared KMITL accounting-dimension filtering for the report models.

    Turns the dimension values selected on screen into ``analytic_distribution``
    domain leaves so reports can restrict the ledger to specific KMITL
    dimensions. Used by the Trial Balance and the Aged Partner Balance reports.
    """

    _name = "accounting_kmitl_reports.dimension.filter.mixin"
    _description = "KMITL Report Dimension Filter Mixin"

    @api.model
    def _kmitl_build_dim_leaves(self, dims, dim_only_self=None):
        """Turn the selected dimension values into ``analytic_distribution``
        domain leaves. Within a dimension the ids (plus descendants by
        default) are OR-ed; the resulting leaves are AND-ed across dimensions
        by the domain builder.

        ``dim_only_self``: optional ``{code: bool}``. When truthy for a
        dimension only the exact selected analytic accounts match; otherwise
        (the default) the selection is expanded to include all of its
        descendants, since the KMITL dimensions are hierarchical.
        """
        analytic = self.env["account.analytic.account"]
        use_child = "parent_id" in analytic._fields
        dim_only_self = dim_only_self or {}
        leaves = []
        for code in DIMENSION_CODES:
            ids = (dims or {}).get(code) or []
            if not ids:
                continue
            if use_child and not dim_only_self.get(code):
                ids = analytic.search([("id", "child_of", ids)]).ids
            leaves.append(("analytic_distribution", "in", ids))
        return leaves

    # ------------------------------------------------------------------
    # Shared expand-detail: one journal entry's posting lines, with the KMITL
    # accounting dimensions resolved per line. Used by every report whose rows
    # expand to the underlying entry (General Ledger, General Journal) so the
    # detail panel looks the same everywhere.
    # ------------------------------------------------------------------
    @api.model
    def _kmitl_move_lines_detail(self, move_ids):
        """``{move_id: [{id, account, label, partner, debit, credit,
        dimensions, dim_text}]}`` for the entries' posting lines."""
        if not move_ids:
            return {}
        rows = self.env["account.move.line"].search_read(
            [
                ("move_id", "in", list(move_ids)),
                ("display_type", "not in", _SKIP_DISPLAY_TYPES),
            ],
            [
                "move_id",
                "account_id",
                "name",
                "partner_id",
                "debit",
                "credit",
                "analytic_distribution",
            ],
        )
        acc_ids = {r["account_id"][0] for r in rows if r["account_id"]}
        acc_name = {
            a.id: ("%s %s" % (a.code or "", a.name or "")).strip()
            for a in self.env["account.account"].browse(list(acc_ids)).exists()
        }
        analytic_ids = set()
        for r in rows:
            for aid in r.get("analytic_distribution") or {}:
                analytic_ids.add(int(aid))
        ana = (
            self.env["account.analytic.account"].browse(list(analytic_ids)).exists()
        )
        ana_map = {
            a.id: (a.root_plan_id.code or "", a.code or "", a.name or "") for a in ana
        }
        dim_labels = {
            "funds": _("Fund"),
            "departments": _("Department"),
            "activities": _("Activity"),
            "sources": _("Source"),
        }

        def build_dims(distribution):
            by_plan = {}
            for aid in distribution or {}:
                plan, code, name = ana_map.get(int(aid), ("", "", ""))
                if plan:
                    by_plan.setdefault(plan, []).append((code, name))
            dims = []
            for plan in DETAIL_DIM_PLANS:
                for code, name in by_plan.get(plan, []):
                    value = ("[%s] %s" % (code, name)).strip() if code else (name or "")
                    dims.append({"label": dim_labels[plan], "value": value})
            return dims

        result = {}
        for r in rows:
            dims = build_dims(r.get("analytic_distribution"))
            result.setdefault(r["move_id"][0], []).append(
                {
                    "id": r["id"],
                    "account": acc_name.get(
                        r["account_id"][0] if r["account_id"] else 0, ""
                    ),
                    "label": r["name"] or "",
                    "partner": r["partner_id"][1] if r["partner_id"] else "",
                    "debit": r["debit"] or 0.0,
                    "credit": r["credit"] or 0.0,
                    "dimensions": dims,
                    "dim_text": " · ".join(
                        "%s: %s" % (d["label"], d["value"]) for d in dims
                    ),
                }
            )
        return result

    @api.model
    def get_move_lines_detail(self, move_id):
        """RPC for the on-screen expand: one entry's posting lines (account,
        label, partner, debit, credit and the KMITL accounting dimensions)."""
        return self._kmitl_move_lines_detail([move_id]).get(move_id, [])

    @api.model
    def get_move_lines_details(self, move_ids):
        """RPC for the "Expand all" toggle: posting lines for several entries
        at once, keyed by move id (so the current page can expand in a single
        round-trip)."""
        return self._kmitl_move_lines_detail(move_ids)

    # ------------------------------------------------------------------
    # Shared filter helpers used by the date-ranged reports (Trial Balance,
    # General Ledger).
    # ------------------------------------------------------------------
    @api.model
    def _kmitl_fy_start_date(self, date_from, company):
        """Fiscal-year start that contains ``date_from`` (used by the OCA
        engines to accumulate P&L opening balances)."""
        if not date_from:
            return False
        if isinstance(date_from, str):
            date_from = fields.Date.to_date(date_from)
        start, _end = date_utils.get_fiscal_year(
            date_from,
            day=company.fiscalyear_last_day,
            month=int(company.fiscalyear_last_month),
        )
        return start

    @api.model
    def _kmitl_apply_account_range(self, options, company_id, account_ids):
        """Expand an optional account code range into ``account_ids`` and
        merge it with any explicitly picked accounts."""
        code_from = options.get("account_code_from_id")
        code_to = options.get("account_code_to_id")
        if code_from and code_to:
            a_from = self.env["account.account"].browse(code_from)
            a_to = self.env["account.account"].browse(code_to)
            if a_from.code and a_to.code:
                ranged = self.env["account.account"].search(
                    [
                        ("company_id", "=", company_id),
                        ("code", ">=", a_from.code),
                        ("code", "<=", a_to.code),
                    ]
                )
                account_ids = list(set(account_ids) | set(ranged.ids))
        return account_ids
