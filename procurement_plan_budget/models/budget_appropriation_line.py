# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan",
        inverse_name="budget_appropriation_line_id",
        string="รายการแผนจัดซื้อจัดจ้าง",
        help="รายการแผนจัดซื้อจัดจ้างที่ใช้เงินจากรหัสงบประมาณนี้",
    )

    procurement_plan = fields.Boolean(
        related="account_id.procurement_plan",
        store=False,
    )

    enable_procurement_plan = fields.Boolean("จัดสรรแผนจัดซื้อจัดจ้าง")
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
    )
    procurement_plan_description = fields.Char(string="ชื่อ")
    procurement_plan_amount = fields.Integer(string="จำนวน")
    procurement_plan_unit = fields.Char("Unit of Measure")

    def _prepare_procurement_plan_valus(self):
        return {
            "date_range_fy_id": self.date_range_fy_id.id,
            "description": self.procurement_plan_description,
            "amount": self.procurement_plan_amount,
            "unit": self.procurement_plan_unit,
            "total_price": self.balance,
            "procurement_method_id": self.procurement_method_id.id,
            "user_id": self.appropriation_id.user_id.id,
            "state": "pending",
        }
