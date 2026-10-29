from odoo import api, fields, models


class AdvancePaymentRelatedDocument(models.Model):
    _inherit = "advance.payment.related.document"

    document_kind = fields.Selection(
        selection_add=[("sarabun", "หนังสือสารบรรณ")],
        ondelete={"sarabun": "set default"},
    )
    document_ref = fields.Reference(
        selection_add=[("sarabun.document", "หนังสือสารบรรณ")],
    )

    @api.model
    def _get_document_kinds(self):
        kinds = super()._get_document_kinds()
        # The register number restarts every fiscal year, so ลงวันที่ tells
        # repeated numbers apart.
        kinds["sarabun"] = ("sarabun.document", "date")
        return kinds

    def _get_document_subject(self, document):
        if document._name == "sarabun.document":
            return (document.subject or "").strip().split("\n")[0] or document.name
        return super()._get_document_subject(document)
