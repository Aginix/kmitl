# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api

from .project_budget_item import BUDGET_TYPE_SELECTION

_logger = logging.getLogger(__name__)


class ProjectBudgetLine(models.Model):
    """One line of a project's Project Budget Plan — an income (รายรับ) or expense
    (รายจ่าย) entry pointing at a catalog Budget Item, with a free-text แตกตัวคูณ
    breakdown and a manually entered amount. Unit and unit price are shown from the
    item as reference only (see ADR-0002). ``category_id`` (the item's ประเภทงบ) is
    what the expense table groups into nested sections."""

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
    budget_item_id = fields.Many2one(
        comodel_name="project.budget.item",
        string="รายการ",
        required=True,
        ondelete="restrict",
        # Scope the picker to the section's ประเภทงบ subtree when one is set (a line
        # added from a section header), otherwise offer every item of the type.
        domain="[('budget_type', '=', budget_type),"
        " ('category_id', 'child_of', category_id)] if category_id"
        " else [('budget_type', '=', budget_type)]",
    )
    # The ประเภทงบ of the chosen item — drives the nested section grouping in the
    # expense table. Stored so the list can order/cluster by it; defaulted per
    # section on add and kept in step with the chosen item via onchange.
    category_id = fields.Many2one(
        comodel_name="project.budget.category",
        string="ประเภทงบ",
        ondelete="restrict",
        index=True,
    )
    # The chosen category's label and materialised path, exposed so the OWL table
    # can build the nested (up to 3-level) section headers client-side without
    # extra RPCs. Stored so the list can also order by the path server-side.
    category_complete_name = fields.Char(
        related="category_id.complete_name", store=True
    )
    category_parent_path = fields.Char(
        related="category_id.parent_path", store=True
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
    # Free to leave blank/zero while drafting; validated at confirmation on the
    # project (kmitl.project.button_new).
    amount = fields.Float(string="จำนวนเงิน", digits="Product Price")

    @api.onchange("budget_item_id")
    def _onchange_budget_item_id(self):
        """Keep the category in step with the chosen item's ประเภทงบ."""
        if self.budget_item_id:
            self.category_id = self.budget_item_id.category_id
