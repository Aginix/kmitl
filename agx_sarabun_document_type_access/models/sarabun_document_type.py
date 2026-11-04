from odoo import api, fields, models


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

    @api.model_create_multi
    def create(self, vals_list):
        self.env["ir.ui.menu"].clear_caches()
        return super().create(vals_list)

    def write(self, vals):
        if "reader_group_ids" in vals or "active" in vals:
            self.env["ir.ui.menu"].clear_caches()
        return super().write(vals)
