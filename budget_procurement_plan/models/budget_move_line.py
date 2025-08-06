# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetMoveLine(models.Model):
    _inherit = "budget.move.line"

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
        "account_id.procurement_plan",
    )
    def _compute_unallocated_balance(self):
        super()._compute_unallocated_balance()
        for rec in self:
            if rec.procurement_plan:
                total_price = sum(rec.procurement_plan_ids.mapped("total_price"))
                rec.unallocated_balance = rec.balance - total_price

    @api.depends("account_id.procurement_plan")
    def _compute_hide_unallocated_balance(self):
        super()._compute_hide_unallocated_balance()
        for line in self:
            if line.account_id.procurement_plan:
                line.hide_unallocated_balance = False
