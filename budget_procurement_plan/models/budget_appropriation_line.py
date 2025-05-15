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
    )
    unallocated_amount = fields.Float(string="ยังไม่ระบุรายการ", help="จำนวนเงินที่ยังไม่มีการวางแผนการใช้งาน แต่ต้องการจองจำนวนเงินไว้ก่อน")
    procurement_plan_ids = fields.Many2many(comodel_name='procurement.plan', string="แผนจัดซื้อจัดจ้าง", help="รายการแผนจัดซื้อจัดจ้างที่ใช้เงินจากรหัสงบประมาณนี้")
    procurement_plan = fields.Boolean(
        related="template_line_id.procurement_plan",
        store=True,
        readonly=True,
    )

    @api.depends('procurement_plan_ids.amount', 'unallocated_amount')
    def _compute_amount(self):
        for rec in self:
            rec.amount = sum(rec.procurement_plan_ids.mapped('total_price')) + rec.unallocated_amount

    def unlink(self):
        for line in self:
            line.procurement_plan_ids.unlink()
        return super().unlink()

    def write(self, vals):
        if 'procurement_plan_ids' in vals:
            for rec in self:
                new_ids = vals['procurement_plan_ids'][0][2]
                current_ids = rec.procurement_plan_ids.ids
                removed_ids = set(current_ids) - set(new_ids)

                if removed_ids:
                    self.env['procurement.plan'].browse(list(removed_ids)).unlink()
        return super().write(vals)
