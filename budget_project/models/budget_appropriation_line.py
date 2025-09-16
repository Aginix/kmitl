# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    project_ids = fields.One2many(
        comodel_name="budget.project",
        inverse_name="budget_appropriation_line_id",
        string="โครงการ/กิจกรรม",
        help="โครงการ/กิจกรรมที่ใช้เงินจากรหัสงบประมาณนี้",
    )

    is_project = fields.Boolean(
        related="account_id.is_project",
        store=True,
    )

    # # TODO: แยกเงินลอยเป็นอีกโมดูลเนื่องจากมีการใช้ร่วมกับ procurement_plan_budget
    # unallocated_balance = fields.Float(
    #     string="ยังไม่ระบุรายการ",
    #     help="จำนวนเงินที่ยังไม่มีการวางแผนการใช้งาน แต่ต้องการจองจำนวนเงินไว้ก่อน",
    #     store=True,
    #     required=False,
    #     digits="Budget",
    #     compute="_compute_unallocated_balance",
    # )

    # hide_unallocated_balance = fields.Boolean(
    #     compute="_compute_hide_unallocated_balance",
    # )

    # @api.depends(
    #     "project_ids.amount",
    #     "balance",
    #     "account_id.is_project",
    # )
    # def _compute_unallocated_balance(self):
    #     for rec in self:
    #         if rec.is_project:
    #             total_price = sum(rec.project_ids.mapped("amount"))
    #             rec.unallocated_balance = rec.balance - total_price

    # @api.depends("account_id.is_project")
    # def _compute_hide_unallocated_balance(self):
    #     for line in self:
    #         if line.account_id.is_project:
    #             line.hide_unallocated_balance = False
