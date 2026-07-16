from odoo import fields, models


class IrModel(models.Model):
    _inherit = "ir.model"

    attachment_doctype_rel_ids = fields.One2many(
        comodel_name="ir.attachment.document.type.rel",
        inverse_name="res_model_id",
        string="Attachment Document Types",
    )
