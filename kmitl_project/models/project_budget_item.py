# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

# budget_type classifies a budget item (and its whole subtree) as either income
# (รายรับ) or expense (รายจ่าย). The former ประเภทงบ categories
# (งบบุคลากร/งบดำเนินงาน/งบอุดหนุน) are no longer selection values here — they are
# now root records of the expense tree, seeded in
# data/project_budget_item_data.xml. Imported by project_budget_line so both
# models stay in sync.
BUDGET_TYPE_SELECTION = [
    ("income", "รายรับ"),
    ("expense", "รายจ่าย"),
]


class ProjectBudgetItem(models.Model):
    """Hierarchical catalog (master data) for the Project Budget Plan. Expense
    roots are the ประเภทงบ categories and their children are the selectable expense
    items; income items are flat (no root). Each item carries a standard
    description, unit and unit price used only as reference when planning; project
    budget lines pick the leaf items. Configured on its own settings page."""

    _name = "project.budget.item"
    _description = "รายการงบประมาณโครงการ"
    _inherit = ["mail.thread"]
    _parent_store = True
    _parent_name = "parent_id"
    _order = "parent_path"
    # Let the picker match what it displays (the full "ประเภทงบ / รายการ" path),
    # not just the leaf name.
    _rec_names_search = ["complete_name", "name"]

    sequence = fields.Integer(default=10)
    name = fields.Char(string="ชื่อรายการ", required=True, tracking=True)
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
        tracking=True,
    )
    # Standard rate-card reference values — informational only (the plan line's
    # amount is entered manually, not computed from these; see ADR-0002).
    description = fields.Text(string="คำอธิบาย", tracking=True)
    unit = fields.Char(string="หน่วยนับ", help="เช่น คน / ครั้ง / วัน", tracking=True)
    unit_price = fields.Float(
        string="ราคาต่อหน่วย", digits="Product Price", tracking=True
    )
    note = fields.Text(string="หมายเหตุ", tracking=True)
    parent_id = fields.Many2one(
        "project.budget.item",
        string="อยู่ภายใต้ประเภทงบ",
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "project.budget.item", "parent_id", string="รายการย่อย"
    )
    active = fields.Boolean(default=True, tracking=True)

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

    def unlink(self):
        """Block deletion of an item that is still in use — as a parent category
        (has children) or referenced by any Project Budget Plan line. The line
        lookup runs sudo so the check is global, not limited to the deleter's
        visible projects. In-use items should be archived instead."""
        for item in self:
            if item.child_ids:
                raise UserError(
                    _(
                        "ไม่สามารถลบ '%s' ได้ เนื่องจากยังมีรายการย่อยอยู่ "
                        "กรุณาลบรายการย่อยก่อน"
                    )
                    % item.complete_name
                )
        used = (
            self.env["project.budget.line"]
            .sudo()
            .search([("budget_item_id", "in", self.ids)])
        )
        if used:
            raise UserError(
                _(
                    "ไม่สามารถลบรายการที่ถูกใช้งานในแผนงบประมาณโครงการอยู่: %s\n"
                    "หากไม่ต้องการใช้แล้ว ให้เก็บถาวร (archive) แทนการลบ"
                )
                % ", ".join(used.budget_item_id.mapped("complete_name"))
            )
        return super().unlink()

    def name_get(self):
        return [(item.id, item.complete_name) for item in self]
