from odoo import fields, models


class SarabunDocumentType(models.Model):
    _inherit = "sarabun.document.type"

    reader_group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="sarabun_document_type_reader_group_rel",
        column1="type_id",
        column2="group_id",
        string="Reader Groups (by OU)",
        help="Members may read (never edit) every non-draft หนังสือ of this type "
        "whose Operating Unit is one of theirs. Empty = route-based access only.",
    )
