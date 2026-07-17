# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# budget_type classifies a budget item (and its whole subtree) as either income
# (รายรับ) or expense (รายจ่าย). The former ประเภทงบ categories
# (งบบุคลากร/งบดำเนินงาน/งบอุดหนุน) are no longer selection values here — they are
# now root records of the expense tree, seeded in
# data/project_expense_item_data.xml. Imported by project_expense so both models
# stay in sync.
BUDGET_TYPE_SELECTION = [
    ("income", "รายรับ"),
    ("expense", "รายจ่าย"),
]


class ProjectExpenseItem(models.Model):
    """Hierarchical master data for project budget items. Expense roots are the
    ประเภทงบ categories and their children are the selectable expense items;
    income items are flat (no root). Configured on its own settings page; project
    budget lines pick the leaf items."""

    _name = "project.expense.item"
    _description = "รายการงบประมาณโครงการ"
    _parent_store = True
    _parent_name = "parent_id"
    _order = "parent_path"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="ชื่อรายการ", required=True)
    complete_name = fields.Char(
        string="รายการ",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
    )
    budget_type = fields.Selection(
        BUDGET_TYPE_SELECTION,
        string="ประเภท",
        required=True,
    )
    parent_id = fields.Many2one(
        "project.expense.item",
        string="อยู่ภายใต้ประเภทงบ",
        ondelete="cascade",
        index=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "project.expense.item", "parent_id", string="รายการย่อย"
    )
    active = fields.Boolean(default=True)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for item in self:
            if item.parent_id:
                item.complete_name = "%s / %s" % (
                    item.parent_id.complete_name,
                    item.name,
                )
            else:
                item.complete_name = item.name

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_("ไม่สามารถสร้างลำดับชั้นแบบวนซ้ำได้"))

    @api.constrains("budget_type", "parent_id")
    def _check_budget_type_consistency(self):
        for item in self:
            if item.parent_id and item.budget_type != item.parent_id.budget_type:
                raise ValidationError(
                    _("ประเภท (รายรับ/รายจ่าย) ต้องตรงกับรายการหลัก")
                )

    @api.onchange("parent_id")
    def _onchange_parent_id(self):
        if self.parent_id:
            self.budget_type = self.parent_id.budget_type

    def name_get(self):
        return [(item.id, item.complete_name) for item in self]
