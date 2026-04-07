from odoo import fields, models


class ResourceEducationDepartment(models.Model):
    _name = "resource.education.department"
    _description = "Resource Education Department"

    name = fields.Char(string="Department Name", required=True, translate=True)
    active = fields.Boolean(default=True)
