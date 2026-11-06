from odoo import fields, models


class ProjectBudgetCategory(models.Model):
    _inherit = "project.budget.category"

    loan_via_pr_only = fields.Boolean(
        string="ยืมผ่านใบ PR เท่านั้น",
        help="รายการค่าใช้จ่ายในหมวดนี้ (และหมวดย่อย) ยืมเงินโครงการโดยตรงไม่ได้ "
        "ต้องยืมผ่านใบขอให้จัดหา (PR)",
    )
