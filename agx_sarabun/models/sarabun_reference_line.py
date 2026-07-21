# -*- coding: utf-8 -*-
from odoo import fields, models


class SarabunReferenceLine(models.Model):
    """อ้างถึง (out-of-system) — a free-text reference to a letter that does not
    exist as a ``sarabun.document`` (e.g. "หนังสือ อว 6801/123 ลว 1 พ.ค.").

    In-system อ้างถึง uses the document's ``reference_document_ids`` m2m instead.
    This replaces the dropped, hardcoded ``sarabun.reference`` ERP-record picker.
    """

    _name = "sarabun.reference.line"
    _description = "Sarabun อ้างถึง (free-text reference)"
    _order = "sequence, id"

    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    text = fields.Char(
        string="Reference",
        required=True,
        help='e.g. "หนังสือ อว 6801/123 ลงวันที่ 1 พฤษภาคม 2569"',
    )
