from odoo import fields, models


class IrAttachmentDocumentTypeRel(models.Model):
    """Per-model configuration of which document types are offered when
    attaching a file, and in what order.

    One row per (res_model, document_type) pair. The classifier widget
    resolves the doctype list for the current form by filtering on
    `res_model_name` (stored + indexed related field) and ordering by
    `sequence`, so no client-side post-filtering is needed.
    """

    _name = "ir.attachment.document.type.rel"
    _description = "Attachment Document Type Mapping"
    _order = "sequence, id"

    res_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
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
        related="res_model_id.model",
        store=True,
        index=True,
        string="Model Technical Name",
    )

    _sql_constraints = [
        (
            "uniq_model_doctype",
            "unique(res_model_id, document_type_id)",
            "This document type is already linked to this model.",
        ),
    ]
