from odoo import fields, models


class IrAttachmentDocumentTypeRel(models.Model):
    """Line inside an `ir.attachment.document.type.config` — one doctype
    on the config's model, at a given `sequence`.

    The patched many2many_binary widget resolves the doctype list for the current form
    by filtering rows on `res_model_name` (stored + indexed related
    field, sourced from `config_id.res_model_name`) and ordering by
    `sequence`. That keeps the widget's query a plain SQL scan of a
    single column, no join or client-side post-filter needed.
    """

    _name = "ir.attachment.document.type.rel"
    _description = "Attachment Document Type Mapping"
    _order = "sequence, id"

    config_id = fields.Many2one(
        comodel_name="ir.attachment.document.type.config",
        string="Model Config",
        required=True,
        ondelete="cascade",
    )
    document_type_id = fields.Many2one(
        comodel_name="ir.attachment.document.type",
        string="Document Type",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    res_model_name = fields.Char(
        related="config_id.res_model_name",
        store=True,
        index=True,
        string="Model Technical Name",
    )

    _sql_constraints = [
        (
            "uniq_config_doctype",
            "unique(config_id, document_type_id)",
            "This document type is already linked to this model.",
        ),
    ]
