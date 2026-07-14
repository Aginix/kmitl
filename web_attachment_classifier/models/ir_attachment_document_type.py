from odoo import api, fields, models


class IrAttachmentDocumentType(models.Model):
    _name = "ir.attachment.document.type"
    _description = "Attachment Document Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    res_model_ids = fields.Many2many(
        comodel_name="ir.model",
        string="Applies to Models",
        help="Parent models where this document type may be assigned to an "
        "attachment. The widget on those forms will offer this doctype in "
        "its dropdown.",
    )
    res_model_names = fields.Char(
        compute="_compute_res_model_names",
        store=True,
        help="Comma-separated technical names of res_model_ids; used by the "
        "widget to filter doctypes for the current form's res_model.",
    )

    @api.depends("res_model_ids.model")
    def _compute_res_model_names(self):
        for rec in self:
            rec.res_model_names = ",".join(rec.res_model_ids.mapped("model"))
