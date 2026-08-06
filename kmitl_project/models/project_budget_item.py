# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

# budget_type classifies a budget item as either income (รายรับ) or expense
# (รายจ่าย). The ประเภทงบ categories (งบบุคลากร/งบดำเนินงาน/งบอุดหนุน) live in their
# own hierarchical model ``project.budget.category``; an expense item points at one
# via ``category_id``. Imported by project_budget_line so both models stay in sync.
BUDGET_TYPE_SELECTION = [
    ("income", "รายรับ"),
    ("expense", "รายจ่าย"),
]


class ProjectBudgetItem(models.Model):
    """Flat catalog (master data) for the Project Budget Plan. Each item is income
    (รายรับ) or expense (รายจ่าย); an expense item is filed under a ประเภทงบ category
    (``project.budget.category``) while income items have none. Each item carries a
    standard description, unit and unit price used only as reference when planning;
    project budget lines pick these items. Configured on its own settings page."""

    _name = "project.budget.item"
    _description = "รายการงบประมาณโครงการ"
    _inherit = ["mail.thread"]
    _order = "budget_type, category_id, sequence, id"
    # Let the picker match what it displays (the full "ประเภทงบ / รายการ" path),
    # not just the item name.
    _rec_names_search = ["complete_name", "name"]

    sequence = fields.Integer(default=10)
    name = fields.Char(string="ชื่อรายการ", required=True, tracking=True)
    complete_name = fields.Char(
        string="รายการ",
        compute="_compute_complete_name",
        store=True,
    )
    budget_type = fields.Selection(
        BUDGET_TYPE_SELECTION,
        string="ประเภท",
        required=True,
        default="expense",
        tracking=True,
    )
    category_id = fields.Many2one(
        "project.budget.category",
        string="ประเภทงบ",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="หมวดประเภทงบของรายการรายจ่าย (งบบุคลากร/งบดำเนินงาน/งบอุดหนุน หรือหมวดย่อย)",
    )
    # Standard rate-card reference values — informational only (the plan line's
    # amount is entered manually, not computed from these; see ADR-0002).
    description = fields.Text(string="คำอธิบาย", tracking=True)
    unit = fields.Char(string="หน่วยนับ", help="เช่น คน / ครั้ง / วัน", tracking=True)
    unit_price = fields.Float(
        string="ราคาต่อหน่วย", digits="Product Price", tracking=True
    )
    note = fields.Text(string="หมายเหตุ", tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    @api.depends("name", "category_id.complete_name")
    def _compute_complete_name(self):
        for item in self:
            if item.category_id:
                item.complete_name = "%s / %s" % (
                    item.category_id.complete_name,
                    item.name,
                )
            else:
                item.complete_name = item.name

    @api.constrains("budget_type", "category_id")
    def _check_category_matches_type(self):
        for item in self:
            if item.budget_type == "expense" and not item.category_id:
                raise ValidationError(_("รายการรายจ่ายต้องระบุประเภทงบ"))
            if item.budget_type == "income" and item.category_id:
                raise ValidationError(_("รายการรายรับต้องไม่มีประเภทงบ"))

    @api.onchange("budget_type")
    def _onchange_budget_type(self):
        """Income items carry no ประเภทงบ — clear it when switching to income."""
        if self.budget_type == "income":
            self.category_id = False

    def unlink(self):
        """Block deletion of an item referenced by any Project Budget Plan line. The
        line lookup runs sudo so the check is global, not limited to the deleter's
        visible projects. In-use items should be archived instead."""
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
        # Display just the leaf name (e.g. "ค่าใช้สอย") — the ประเภทงบ context is
        # already carried by the table's section header, so the full path would only
        # be noise in the picked value. Search still matches the full path via
        # _rec_names_search, and complete_name is used explicitly where the path is
        # needed (portal, config column, validation messages).
        return [(item.id, item.name) for item in self]
