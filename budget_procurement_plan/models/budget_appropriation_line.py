# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = 'budget.appropriation.line'

    unallocated_amount = fields.Float(string="ยังไม่ระบุรายการ", help="จำนวนเงินที่ยังไม่มีการวางแผนการใช้งาน แต่ต้องการจองจำนวนเงินไว้ก่อน")
    procurement_plan_ids = fields.Many2many(comodel_name='procurement.plan', string="แผนจัดซื้อจัดจ้าง", help="รายการแผนจัดซื้อจัดจ้างที่ใช้เงินจากรหัสงบประมาณนี้")
    procurement_plan = fields.Boolean(
        related="template_line_id.procurement_plan",
        store=True,
        readonly=True,
    )
