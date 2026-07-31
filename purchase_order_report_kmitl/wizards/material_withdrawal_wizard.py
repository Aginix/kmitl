# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class POMaterialWithdrawalWizard(models.TransientModel):
    _name = "purchase.order.material.withdrawal.wizard"
    _description = "พิมพ์ใบเบิกวัสดุ (พ.43) จาก PO"

    order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="ใบสั่งซื้อ",
        required=True,
        ondelete="cascade",
    )
    requester_id = fields.Many2one(
        comodel_name="hr.employee",
        string="ผู้ขอเบิก/ผู้รับของ",
        required=True,
    )
    dept_head_id = fields.Many2one(
        comodel_name="hr.employee",
        string="หัวหน้าหน่วยงาน",
        required=True,
    )
    disburser_id = fields.Many2one(
        comodel_name="hr.employee",
        string="ผู้เบิกจ่าย",
        required=True,
    )

    def action_print(self):
        self.ensure_one()
        if not self.order_id.order_line:
            raise UserError(_("ไม่มีรายการใน PO นี้"))
        return self.env.ref(
            "purchase_order_report_kmitl.action_report_material_withdrawal"
        ).report_action(
            self.order_id,
            data={
                "requester_id": self.requester_id.id,
                "dept_head_id": self.dept_head_id.id,
                "disburser_id": self.disburser_id.id,
            },
            config=False,
        )
