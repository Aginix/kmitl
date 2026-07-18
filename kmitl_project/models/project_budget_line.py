# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from .project_budget_item import BUDGET_TYPE_SELECTION

_logger = logging.getLogger(__name__)


class ProjectBudgetLine(models.Model):
    """One line of a project's Project Budget Plan — an income (รายรับ) or expense
    (รายจ่าย) entry pointing at a catalog Budget Item, with a free-text แตกตัวคูณ
    breakdown and a manually entered amount. Unit and unit price are shown from
    the item as reference only (see ADR-0002). budget_category_id (the item's root
    ประเภทงบ) is what the expense table groups into sections."""

    _name = "project.budget.line"
    _description = "บรรทัดแผนงบประมาณโครงการ"
    _order = "budget_type, budget_category_id, sequence, id"

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
    budget_item_id = fields.Many2one(
        comodel_name="project.budget.item",
        string="รายการ",
        required=True,
        ondelete="restrict",
        # Scope the picker to the section's category when one is set (a line added
        # from a section header), otherwise offer every item of the type.
        domain="[('budget_type', '=', budget_type), ('child_ids', '=', False),"
        " ('parent_id', '=', budget_category_id)] if budget_category_id"
        " else [('budget_type', '=', budget_type), ('child_ids', '=', False)]",
    )
    # The expense root (ประเภทงบ) of the chosen item — drives the section grouping
    # in the expense table. Stored so the list can order/cluster by it; defaulted
    # per section on add and kept in step with the chosen item via onchange.
    budget_category_id = fields.Many2one(
        comodel_name="project.budget.item",
        string="ประเภทงบ",
        ondelete="restrict",
    )
    # Reference only — the standard rate carried by the chosen item.
    unit = fields.Char(
        string="หน่วยนับ", related="budget_item_id.unit", readonly=True
    )
    unit_price = fields.Float(
        string="ราคาต่อหน่วย",
        related="budget_item_id.unit_price",
        readonly=True,
        digits="Product Price",
    )
    description = fields.Text(
        string="คำอธิบาย",
        help="สำหรับอธิบายการแตกตัวคูณ เช่น 50 คน x 200 บาท x 3 วัน",
    )
    amount = fields.Float(string="จำนวนเงิน", digits="Product Price", required=True)
    note = fields.Char(string="หมายเหตุ")

    @api.onchange("budget_item_id")
    def _onchange_budget_item_id(self):
        """Keep the category in step with the chosen item's root."""
        if self.budget_item_id:
            self.budget_category_id = self.budget_item_id.parent_id

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("จำนวนเงินต้องมากกว่าศูนย์"))
