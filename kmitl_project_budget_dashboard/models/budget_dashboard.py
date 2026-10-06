from odoo import models


class BudgetDashboard(models.AbstractModel):
    """Register the โครงการ/กิจกรรม Pool Tag with the ตรวจสอบงบประมาณ report.

    The report lists the tag's items under each budget code that holds them
    (see budget_dashboard_pool_tag); budget core never knows this dimension.
    """

    _inherit = "budget.dashboard"

    def _pool_tags(self):
        return super()._pool_tags() + [
            {
                "field": "kmitl_project_analytic_id",
                "label": "โครงการ/กิจกรรม",
                "toggle_label": "แสดงโครงการ/กิจกรรม",
                "res_model": "kmitl.project",
                "res_field": "analytic_account_id",
            }
        ]
