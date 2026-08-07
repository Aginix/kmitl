# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api

from .project_budget_item import BUDGET_TYPE_SELECTION

_logger = logging.getLogger(__name__)


class ProjectBudgetLine(models.Model):
    """One line of a project's Project Budget Plan — an income (รายรับ) or expense
    (รายจ่าย) entry. Its identity is a free-text ``name`` typed by the planner; a
    catalog Budget Item may optionally be picked to pre-fill the name (and its
    reference unit/price). ``category_id`` (ประเภทงบ) is what the expense table
    groups into nested sections. The amount is entered manually (see ADR-0002)."""

    _name = "project.budget.line"
    _description = "บรรทัดแผนงบประมาณโครงการ"
    _order = "budget_type, category_parent_path, sequence, id"

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
    # Free-text label of the line. Required so every line is identified; a picked
    # catalog item fills it, but it can equally be typed by hand.
    name = fields.Char(string="รายการ", required=True)
    # The ประเภทงบ this line belongs to — set directly on expense lines (or defaulted
    # from the section it is added under), and drives the nested section grouping in
    # the expense table. Income lines have none.
    category_id = fields.Many2one(
        comodel_name="project.budget.category",
        string="ประเภทงบ",
        ondelete="restrict",
        index=True,
    )
    # Optional convenience — pick a catalog Budget Item to pre-fill name/category and
    # carry its reference unit/price. Not required: lines may be pure free text.
    budget_item_id = fields.Many2one(
        comodel_name="project.budget.item",
        string="เลือกจากรายการ",
        ondelete="restrict",
        # Scope the picker to the section's ประเภทงบ subtree when one is set (a line
        # added from a section header), otherwise offer every item of the type.
        domain="[('budget_type', '=', budget_type),"
        " ('category_id', 'child_of', category_id)] if category_id"
        " else [('budget_type', '=', budget_type)]",
    )
    # A free-text line (added via "เพิ่มอื่น ๆ") vs one picked from the catalog (added
    # via "เพิ่มจากรายการ"). Drives the table: custom lines hide the catalog picker and
    # show only รายการ / คำอธิบาย / จำนวนเงิน. Set from the add button's context.
    is_custom = fields.Boolean(string="พิมพ์เอง", default=False)
    # The chosen category's label and materialised path, exposed so the OWL table
    # can build the nested section headers client-side without extra RPCs. Stored so
    # the list can also order by the path server-side.
    category_complete_name = fields.Char(
        related="category_id.complete_name", store=True
    )
    category_parent_path = fields.Char(
        related="category_id.parent_path", store=True
    )
    # Reference only — the standard rate carried by the chosen item (if any).
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
    # Free to leave blank/zero while drafting; validated at confirmation on the
    # project (kmitl.project.button_new).
    amount = fields.Float(string="จำนวนเงิน", digits="Product Price")

    @api.onchange("budget_item_id")
    def _onchange_budget_item_id(self):
        """Picking a catalog item pre-fills the free-text name and the ประเภทงบ
        (income items carry none). Typing a name by hand needs no item."""
        if self.budget_item_id:
            self.name = self.budget_item_id.name
            self.category_id = self.budget_item_id.category_id
