# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class MaterialWithdrawalWizard(models.TransientModel):
    _name = "purchase.request.approval.material.withdrawal.wizard"
    _description = "พิมพ์ใบเบิกวัสดุ (พ.43) จาก พจ.1"

    approval_id = fields.Many2one(
        comodel_name="purchase.request.approval",
        string="พจ.1",
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
        if not self.approval_id.line_ids:
            raise UserError(_("ไม่มีรายการวัสดุใน พจ.1 นี้"))
        return self.env.ref(
            "purchase_request_approval.action_report_material_withdrawal"
        ).report_action(
            self.approval_id,
            data={
                "requester_id": self.requester_id.id,
                "dept_head_id": self.dept_head_id.id,
                "disburser_id": self.disburser_id.id,
            },
            config=False,
        )
