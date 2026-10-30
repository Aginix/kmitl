from odoo import api, fields, models


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    use_ztree_widget = fields.Boolean(
        string="Tree Selection",
        help="Browse this plan's analytic accounts as an expandable tree "
        "(by parent/child) when picking one in the analytic distribution "
        "widget, instead of only the flat search.",
    )

    @api.model
    def get_relevant_plans(self, **kwargs):
        plans = super().get_relevant_plans(**kwargs)
        use_ztree_by_id = {
            plan.id: plan.use_ztree_widget
            for plan in self.browse([p["id"] for p in plans])
        }
        for plan in plans:
            plan["use_ztree_widget"] = use_ztree_by_id.get(plan["id"], False)
        return plans
