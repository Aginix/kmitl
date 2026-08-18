from odoo import fields, models


class BudgetAccount(models.Model):
    _inherit = "budget.account"

    cross_chargeable = fields.Boolean(
        string="ถัวจ่ายได้",
        help=(
            "ติ๊กถูกเพื่ออนุญาตให้รหัสนี้ถัวจ่ายร่วมกับรหัสอื่นในใบจองเดียวได้ "
            "ใบจองจะมีหลายรหัสได้ก็ต่อเมื่อทุกรหัสติ๊กถัวจ่ายได้ด้วยกัน"
        ),
        default=False,
        copy=True,
        tracking=True,
    )
