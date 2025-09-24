from odoo import fields, models


class BudgetAccount(models.Model):
    _inherit = "budget.account"

    is_project = fields.Boolean(
        string="เป็นโครงการ/กิจกรรม",
        help="หากติ๊กถูก รหัสงบประมาณนี้จะต้องระบุเงินผ่านโครงการ/กิจกรรมเท่านั้น",
        tracking=True,
        default=False,
    )
