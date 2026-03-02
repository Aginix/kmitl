from odoo import fields, models


class KrisProjectCategory(models.Model):
    _name = "kris.project.category"
    _description = "KRIS Project Category"
    _order = "sequence, id"

    name = fields.Char(
        string="หมวดหมู่",
        required=True,
    )
    sequence = fields.Integer(
        string="ลำดับ",
        default=10,
    )
    type_ids = fields.One2many(
        comodel_name="kris.project.type",
        inverse_name="category_id",
        string="ประเภทย่อย",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )


class KrisProjectType(models.Model):
    _name = "kris.project.type"
    _description = "KRIS Project Type"
    _order = "category_id, sequence, id"

    name = fields.Char(
        string="ประเภทย่อย",
        required=True,
    )
    category_id = fields.Many2one(
        comodel_name="kris.project.category",
        string="หมวดหมู่",
        required=True,
        ondelete="restrict",
    )
    sequence = fields.Integer(
        string="ลำดับ",
        default=10,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
