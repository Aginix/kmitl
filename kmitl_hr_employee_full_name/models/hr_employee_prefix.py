from odoo import fields, models


class HrEmployeePrefix(models.Model):
    _name = "hr.employee.prefix"
    _description = "HR Employee Prefix"

    _rec_name = "name"

    name = fields.Char("Prefix", required=True, translate=True)

    _sql_constraints = [
        ("name", "unique(name)", "Can't be duplicate value for this field! -> 'Name'")
    ]

    active = fields.Boolean(default=True)
