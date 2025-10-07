from odoo import fields, models


class BudgetAccount(models.Model):
    _inherit = "budget.account"

    is_project = fields.Boolean(
        string="เป็นโครงการ/กิจกรรม/โครงการยุทธศาสตร์",
        help="หากติ๊กถูก รหัสงบประมาณนี้จะต้องระบุเงินผ่านโครงการ/กิจกรรม/โครงการยุทธศาสตร์เท่านั้น",
        tracking=True,
        default=False,
    )

    project_type = fields.Selection(
        [("project", "Project/Activity"), ("strategic_project", "Strategic Project")],
        tracking=True,
    )
