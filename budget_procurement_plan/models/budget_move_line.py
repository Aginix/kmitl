# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetMoveLine(models.Model):
    _inherit = "budget.move.line"

    unallocated_balance = fields.Float(
        string="ยังไม่ระบุรายการ",
        help="จำนวนเงินที่ยังไม่มีการวางแผนการใช้งาน แต่ต้องการจองจำนวนเงินไว้ก่อน",
        store=True,
        required=False,
        compute="_compute_amount",
    )
    procurement_plan_ids = fields.One2many(
        comodel_name="procurement.plan",
        inverse_name="budget_move_line_id",
        string="แผนจัดซื้อจัดจ้าง",
        help="รายการแผนจัดซื้อจัดจ้างที่ใช้เงินจากรหัสงบประมาณนี้",
    )
    procurement_plan = fields.Boolean(
        related="account_id.procurement_plan",
        store=False,
        readonly=True,
    )

    @api.depends(
        "procurement_plan_ids.amount",
        "procurement_plan_ids.price_per_unit",
        "procurement_plan_ids.total_price",
        "balance",
    )
    def _compute_amount(self):
        for rec in self:
            if rec.procurement_plan:
                total_price = sum(rec.procurement_plan_ids.mapped("total_price"))
                rec.unallocated_balance = rec.balance - total_price
            else:
                rec.unallocated_balance = rec.balance + rec.unallocated_balance
