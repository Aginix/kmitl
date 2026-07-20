from odoo import fields, models


class AttachmentClassifierModelConfig(models.Model):
    """One row per parent model that offers Document Type classification.

    Wraps a target `ir.model` and its ordered list of doctype mappings.
    This is the record users create/edit from Settings — "New" makes a
    config, not a new ir.model, so no Studio-style side effect (manual
    Python model + DB table creation) can happen.
    """

    _name = "attachment.classifier.model.config"
    _description = "Attachment Doctype Config"
    _rec_name = "res_model_id"
    _order = "res_model_id"

    res_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
    )
    res_model_name = fields.Char(
        related="res_model_id.model",
        store=True,
        index=True,
        string="Model Technical Name",
    )
    line_ids = fields.One2many(
        comodel_name="ir.attachment.document.type.rel",
        inverse_name="config_id",
        string="Document Types",
    )

    _sql_constraints = [
        (
            "uniq_res_model",
            "unique(res_model_id)",
            "This model already has a Document Type configuration.",
        ),
    ]
