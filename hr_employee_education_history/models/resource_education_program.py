from odoo import fields, models


class ResourceEducationProgram(models.Model):
    _name = "resource.education.program"
    _description = "Resource Education Program"

    name = fields.Char(string="Program Name", required=True, translate=True)
    active = fields.Boolean(default=True)
