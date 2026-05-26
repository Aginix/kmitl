import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class KrisProjectAllocationItem(models.Model):
    _name = "kris.project.allocation.item"
    _description = "KRIS Allocation Item"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)


class KrisProjectAllocationTemplate(models.Model):
    _name = "kris.project.allocation.template"
    _description = "KRIS Allocation Template"
    _order = "name"

    name = fields.Char(string="Template Name", required=True)
    line_ids = fields.One2many(
        comodel_name="kris.project.allocation.template.line",
        inverse_name="template_id",
        string="List",
    )
    active = fields.Boolean(string="Active", default=True)


class KrisProjectAllocationTemplateLine(models.Model):
    _name = "kris.project.allocation.template.line"
    _description = "KRIS Allocation Template Line"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="kris.project.allocation.template",
        string="แม่แบบ",
        required=True,
        ondelete="cascade",
    )
    item_id = fields.Many2one(
        comodel_name="kris.project.allocation.item",
        string="Allocator",
        required=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    allocation_pct = fields.Float(string="Allocation %", digits=(5, 2))
    department_budget_code_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="รหัสงบประมาณหน่วยงาน",
        domain=[("root_plan_id.code", "=", "departments")],
    )
    is_locked = fields.Boolean(string="ห้ามแก้ไข")
