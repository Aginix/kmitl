# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class ProjectBudgetCategory(models.Model):
    """Hierarchical master data for ประเภทงบ — the expense budget-type categories
    (งบบุคลากร / งบดำเนินงาน / งบอุดหนุน and any sub-levels, in practice up to three).
    A Budget Item (``project.budget.item``) is filed under one category, and the
    Project Budget Plan's expense table groups its lines into nested sections that
    follow this hierarchy. Expense-only — income has no ประเภทงบ. Configured on its
    own settings page with tracking, archive and a delete guard."""

    _name = "project.budget.category"
    _description = "ประเภทงบ"
    _inherit = ["mail.thread"]
    _parent_store = True
    _parent_name = "parent_id"
    _order = "parent_path"
    # Let the picker match what it displays (the full "งบดำเนินงาน / ..." path).
    _rec_names_search = ["complete_name", "name"]

    sequence = fields.Integer(default=10)
    name = fields.Char(string="ชื่อประเภทงบ", required=True, tracking=True)
    complete_name = fields.Char(
        string="ประเภทงบ",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
    )
    parent_id = fields.Many2one(
        "project.budget.category",
        string="อยู่ภายใต้",
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "project.budget.category", "parent_id", string="ประเภทงบย่อย"
    )
    active = fields.Boolean(default=True, tracking=True)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for cat in self:
            if cat.parent_id:
                cat.complete_name = "%s / %s" % (
                    cat.parent_id.complete_name,
                    cat.name,
                )
            else:
                cat.complete_name = cat.name

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_("ไม่สามารถสร้างลำดับชั้นแบบวนซ้ำได้"))

    def unlink(self):
        """Block deletion of a category still in use — as a parent (has children),
        as the ประเภทงบ of a Budget Item, or referenced by a Project Budget Plan
        line. Item/line lookups run sudo so the check is global, not limited to the
        deleter's visible projects. In-use categories should be archived instead."""
        for cat in self:
            if cat.child_ids:
                raise UserError(
                    _(
                        "ไม่สามารถลบ '%s' ได้ เนื่องจากยังมีประเภทงบย่อยอยู่ "
                        "กรุณาลบประเภทงบย่อยก่อน"
                    )
                    % cat.complete_name
                )
        used_items = (
            self.env["project.budget.item"]
            .sudo()
            .search([("category_id", "in", self.ids)])
        )
        if used_items:
            raise UserError(
                _(
                    "ไม่สามารถลบประเภทงบที่มีรายการงบประมาณใช้อยู่: %s\n"
                    "หากไม่ต้องการใช้แล้ว ให้เก็บถาวร (archive) แทนการลบ"
                )
                % ", ".join(used_items.category_id.mapped("complete_name"))
            )
        used_lines = (
            self.env["project.budget.line"]
            .sudo()
            .search([("category_id", "in", self.ids)])
        )
        if used_lines:
            raise UserError(
                _(
                    "ไม่สามารถลบประเภทงบที่ถูกใช้ในแผนงบประมาณโครงการอยู่\n"
                    "หากไม่ต้องการใช้แล้ว ให้เก็บถาวร (archive) แทนการลบ"
                )
            )
        return super().unlink()

    def name_get(self):
        return [(cat.id, cat.complete_name) for cat in self]
