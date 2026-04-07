from odoo import fields, models


class ResourceEducationFaculty(models.Model):
    _name = "resource.education.faculty"
    _description = "Resource Education Faculty"

    name = fields.Char(string="Faculty Name", required=True, translate=True)
    active = fields.Boolean(default=True)
