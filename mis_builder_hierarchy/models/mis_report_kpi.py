from odoo import _, api, fields, models


class MisReportKpi(models.Model):
    _inherit = "mis.report.kpi"

    auto_expand_accounts_hierarchical = fields.Boolean(
        string="Expand as hierarchy",
        help="When 'Display details by account' is set, render detail rows as a "
        "tree using the source model's parent_id field (e.g. account.account, "
        "account.analytic.account). Parent rows auto-aggregate child values.",
    )
    auto_expand_accounts_rollup = fields.Selection(
        [("sum", "Sum"), ("none", "None")],
        string="Hierarchy rollup",
        default="sum",
        help="How parent rows are computed from children. "
        "Sum: parent value = own value + sum of descendants. "
        "None: parent shows only its own direct value.",
    )

    @api.onchange("auto_expand_accounts")
    def _onchange_auto_expand_accounts(self):
        if not self.auto_expand_accounts:
            self.auto_expand_accounts_hierarchical = False
