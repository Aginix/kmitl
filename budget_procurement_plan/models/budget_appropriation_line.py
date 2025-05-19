# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = 'budget.appropriation.line'

    amount = fields.Float(
        digits="Budget Precision",
        help="Amount",
        compute="_compute_amount",
        store=True
    )
    unallocated_amount = fields.Float(string="ยังไม่ระบุรายการ", help="จำนวนเงินที่ยังไม่มีการวางแผนการใช้งาน แต่ต้องการจองจำนวนเงินไว้ก่อน")
    procurement_plan_ids = fields.One2many(comodel_name='procurement.plan',inverse_name="budget_appropriation_line_id", string="แผนจัดซื้อจัดจ้าง", help="รายการแผนจัดซื้อจัดจ้างที่ใช้เงินจากรหัสงบประมาณนี้")
    procurement_plan = fields.Boolean(
        related="template_line_id.procurement_plan",
        store=False,
        readonly=True,
    )

    @api.depends('procurement_plan_ids.amount', 'unallocated_amount')
    def _compute_amount(self):
        for rec in self:
            rec.amount = sum(rec.procurement_plan_ids.mapped('total_price')) + rec.unallocated_amount
