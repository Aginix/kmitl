from odoo import fields, models


class KrisProjectType(models.Model):
    _name = "kris.project.type"
    _description = "KRIS Project Type"
    _order = "category, sequence, id"

    name = fields.Char(
        string="ประเภทโครงการ",
        required=True,
    )
    category = fields.Selection(
        selection=[
            ("academic_service", "งานบริการวิชาการ"),
            ("research", "งานวิจัย"),
        ],
        string="หมวดหมู่",
        required=True,
    )
    sequence = fields.Integer(
        string="ลำดับ",
        default=10,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
