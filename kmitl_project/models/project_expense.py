# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from .project_expense_item import BUDGET_TYPE_SELECTION

_logger = logging.getLogger(__name__)


class ProjectExpense(models.Model):
    """A planned project expense (รายจ่ายโครงการ) — one line under a budget type,
    pointing at a configured expense item with its แตกตัวคูณ breakdown and amount."""

    _name = "project.expense"
    _description = "รายจ่ายโครงการ"
    _order = "budget_type, sequence, id"

    sequence = fields.Integer(default=10)
    project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="โครงการ",
        required=True,
        ondelete="cascade",
    )
    budget_type = fields.Selection(
        BUDGET_TYPE_SELECTION,
        string="ประเภทงบ",
        required=True,
    )
    expense_item_id = fields.Many2one(
        comodel_name="project.expense.item",
        string="รายการค่าใช้จ่าย",
        required=True,
        domain="[('budget_type', '=', budget_type)]",
    )
    description = fields.Text(
        string="คำอธิบาย",
        help="สำหรับอธิบายการแตกตัวคูณ เช่น 50 คน x 200 บาท x 3 วัน",
    )
    amount = fields.Float(string="จำนวนเงิน", digits="Product Price", required=True)
    note = fields.Char(string="หมายเหตุ")

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("จำนวนเงินต้องมากกว่าศูนย์"))
