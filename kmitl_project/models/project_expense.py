# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from .project_expense_item import BUDGET_TYPE_SELECTION

_logger = logging.getLogger(__name__)


class ProjectExpense(models.Model):
    """A planned project budget line — one income (รายรับ) or expense (รายจ่าย)
    line pointing at a configured leaf item, with its แตกตัวคูณ breakdown and
    amount."""

    _name = "project.expense"
    _description = "รายรับ/รายจ่ายโครงการ"
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
        string="ประเภท",
        required=True,
    )
    expense_item_id = fields.Many2one(
        comodel_name="project.expense.item",
        string="รายการ",
        required=True,
        domain="[('budget_type', '=', budget_type), ('child_ids', '=', False)]",
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
