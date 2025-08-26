# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    procurement_plan_ids = fields.One2many(
        comodel_name="procurement.plan",
        inverse_name="budget_appropriation_line_id",
        string="แผนจัดซื้อจัดจ้าง",
        help="รายการแผนจัดซื้อจัดจ้างที่ใช้เงินจากรหัสงบประมาณนี้",
    )

    procurement_plan = fields.Boolean(
        related="account_id.procurement_plan",
        store=False,
        readonly=True,
    )

    # TODO: แยกเงินลอยเป็นอีกโมดูลเนื่องจากมีการใช้ร่วมกับ project_budget
    unallocated_balance = fields.Float(
        string="ยังไม่ระบุรายการ",
        help="จำนวนเงินที่ยังไม่มีการวางแผนการใช้งาน แต่ต้องการจองจำนวนเงินไว้ก่อน",
        store=True,
        required=False,
        digits="Budget",
        compute="_compute_unallocated_balance",
    )

    hide_unallocated_balance = fields.Boolean(
        compute="_compute_hide_unallocated_balance", readonly=True
    )

    @api.depends(
        "procurement_plan_ids.amount",
        "procurement_plan_ids.price_per_unit",
        "procurement_plan_ids.total_price",
        "balance",
        "account_id.procurement_plan",
    )
    def _compute_unallocated_balance(self):
        for rec in self:
            if rec.procurement_plan:
                total_price = sum(rec.procurement_plan_ids.mapped("total_price"))
                rec.unallocated_balance = rec.balance - total_price

    @api.depends("account_id.procurement_plan")
    def _compute_hide_unallocated_balance(self):
        for line in self:
            if line.account_id.procurement_plan:
                line.hide_unallocated_balance = False

    def budget_move_line_vals(self):
        vals = super().budget_move_line_vals()
        if self.procurement_plan:
            vals["balance"] = self.unallocated_balance
        return vals
