# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CapitalExpenditure(models.Model):
    _name = "capital.expenditure"
    _description = "แผนการจัดซื้อจัดจ้าง"

    name = fields.Char(string="ชื่อรายการ", required=True)
    expected_purchase_date = fields.Date(string="วันที่คาดว่าจะจัดซื้อจัดจ้าง")
    note = fields.Text(string="หมายเหตุ")

    payment = fields.Selection(
        [
            ("single", "ไม่มีการแบ่งงวด"),
            ("installment", "แบ่งจ่ายเป็นงวด"),
        ],
        string="แผนการเบิกจ่าย",
        required=True,
        default="single",
    )

    amount = fields.Float(string="จำนวนเงิน", required=False)

    line_ids = fields.One2many(
        "capital.expenditure.payment.line",
        "expenditure_id",
        string="งวดการจ่าย",
    )
    budget_plan_line_id = fields.Many2one(
        "budget.plan.line",
        string="Budget Plan line",
        ondelete="cascade",
    )

    @api.onchange("payment_plan")
    def _onchange_payment_plan(self):
        """ซ่อน field จำนวนเงิน ถ้าเลือก 'แบ่งจ่ายเป็นงวด'"""
        if self.payment_plan == "single":
            self.installment_ids = [(5, 0, 0)]  # เคลียร์งวดการจ่าย
        else:
            self.amount = 0.0  # รีเซ็ตจำนวนเงิน


class CapitalExpenditurePaymentLine(models.Model):
    _name = "capital.expenditure.payment.line"
    _description = "งวดการเบิกจ่าย"

    expenditure_id = fields.Many2one("capital.expenditure", string="แผนการจัดซื้อจัดจ้าง")
    installment_date = fields.Date(string="วันที่")
    installment_amount = fields.Float(string="จำนวนเงิน")
