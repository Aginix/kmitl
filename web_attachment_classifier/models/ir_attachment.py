from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    document_type_id = fields.Many2one(
        comodel_name="ir.attachment.document.type",
        string="Document Type",
        ondelete="restrict",
    )
