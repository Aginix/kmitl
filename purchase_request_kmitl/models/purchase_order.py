from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        tracking=True,
    )
    requesting_department_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Requesting Department",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
        help="ส่วนงานผู้ขอให้จัดหา — ไม่จำเป็นต้องตรงกับส่วนงานของงบประมาณ",
    )
