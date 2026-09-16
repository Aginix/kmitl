from odoo import api, fields, models


class MisReportKpi(models.Model):
    _inherit = "mis.report.kpi"

    auto_expand_accounts_hierarchical = fields.Boolean(
        string="Expand as hierarchy",
        help="When 'Display details by account' is set, render detail rows as a "
        "tree using the source model's parent_id (parent_path). Parent rows are "
        "created automatically; child values are aggregated bottom-up.",
    )
    auto_expand_accounts_rollup = fields.Boolean(
        string="Rollup children into parents",
        default=True,
        help="When set, parent rows display the sum of their own value and "
        "all descendant values. Otherwise parents show only their own value.",
    )

    @api.onchange("auto_expand_accounts")
    def _onchange_auto_expand_accounts(self):
        if not self.auto_expand_accounts:
            self.auto_expand_accounts_hierarchical = False
