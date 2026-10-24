from odoo import fields, models


class HrEmployeeRelativeRelation(models.Model):
    _name = "hr.employee.relative.relation"
    _description = "HR Employee Relative Relation"
    _order = "sequence"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="Relation", required=True, translate=True)
