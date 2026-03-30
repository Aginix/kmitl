from odoo import fields, models


class ResourceEducationLevel(models.Model):
    _name = "resource.education.level"
    _description = "Resource Education Level"

    name = fields.Char(string="Level Name", required=True, translate=True)
    active = fields.Boolean(default=True)
    level = fields.Integer(required=False)
