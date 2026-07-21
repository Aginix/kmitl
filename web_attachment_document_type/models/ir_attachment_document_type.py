from odoo import fields, models


class IrAttachmentDocumentType(models.Model):
    _name = "ir.attachment.document.type"
    _description = "Attachment Document Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "uniq_name",
            "unique(name)",
            "A document type with this name already exists.",
        ),
    ]
