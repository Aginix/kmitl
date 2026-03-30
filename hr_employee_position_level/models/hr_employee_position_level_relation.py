from odoo import fields, models


class HrEmployeePositionLevelRelation(models.Model):
    _name = "hr.employee.position.level.relation"
    _description = "HR Employee Position Level Relation"

    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Position Level Name", required=True, translate=True, tracking=True
    )
    level = fields.Float(tracking=True)
    role = fields.Selection(
        [
            ("academic", "Academic"),
            ("support", "Support"),
        ],
        required=True,
        default="academic",
        tracking=True,
    )
