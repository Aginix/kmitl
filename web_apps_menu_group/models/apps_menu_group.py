from odoo import fields, models


class WebAppsMenuGroup(models.Model):
    _name = "web.apps.menu.group"
    _description = "Apps Menu Group"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("uniq_name", "unique(name)", "A group with this name already exists."),
    ]
