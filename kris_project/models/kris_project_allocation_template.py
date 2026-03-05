import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class KrisProjectAllocationItem(models.Model):
    _name = "kris.project.allocation.item"
    _description = "KRIS Allocation Item"
    _order = "sequence, id"

    name = fields.Char(string="ชื่อ", required=True)
    sequence = fields.Integer(string="ลำดับ", default=10)
    active = fields.Boolean(string="ใช้งาน", default=True)


class KrisProjectAllocationTemplate(models.Model):
    _name = "kris.project.allocation.template"
    _description = "KRIS Allocation Template"
    _order = "name"

    name = fields.Char(string="ชื่อแม่แบบ", required=True)
    line_ids = fields.One2many(
        comodel_name="kris.project.allocation.template.line",
        inverse_name="template_id",
        string="รายการ",
    )
    active = fields.Boolean(string="ใช้งาน", default=True)


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
        string="ผู้รับจัดสรร",
        required=True,
    )
    sequence = fields.Integer(string="ลำดับ", default=10)
    allocation_pct = fields.Float(string="% จัดสรร", digits=(5, 2))
