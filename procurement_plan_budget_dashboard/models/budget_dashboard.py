from odoo import models


class BudgetDashboard(models.AbstractModel):
    """Register the แผนจัดซื้อจัดจ้าง Pool Tag with the ตรวจสอบงบประมาณ report.

    The report lists the tag's items under each budget code that holds them
    (see budget_dashboard_pool_tag); budget core never knows this dimension.
    """

    _inherit = "budget.dashboard"

    def _pool_tags(self):
        return super()._pool_tags() + [
            {
                "field": "procurement_plan_analytic_id",
                "label": "แผนจัดซื้อจัดจ้าง",
                "toggle_label": "แสดงแผนจัดซื้อจัดจ้าง",
                "res_model": "procurement.plan",
                "res_field": "analytic_account_id",
            }
        ]
