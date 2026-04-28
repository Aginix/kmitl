from odoo import fields, models


class KrisProjectCategory(models.Model):
    _name = "kris.project.category"
    _description = "KRIS Project Category"
    _order = "sequence, id"

    name = fields.Char(
        string="Category",
        required=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    type_ids = fields.One2many(
        comodel_name="kris.project.type",
        inverse_name="category_id",
        string="Project Type",
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
        string="Project Type",
        required=True,
    )
    category_id = fields.Many2one(
        comodel_name="kris.project.category",
        string="Category",
        required=True,
        ondelete="restrict",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
