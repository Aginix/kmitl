from odoo import fields, models


class HrEmployeeDecorationRelation(models.Model):
    _name = "hr.employee.decoration.relation"
    _description = "HR Employee Decoration Relation"
    _order = "level asc"

    name = fields.Char(required=True)
    level = fields.Float()
    abbreviation = fields.Char()
