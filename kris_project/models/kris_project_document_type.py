from odoo import fields, models


class KrisProjectDocumentType(models.Model):
    _name = "kris.project.document.type"
    _description = "KRIS Project Document Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
