# -*- coding: utf-8 -*-
from odoo import fields, models


class SarabunEnclosure(models.Model):
    """สิ่งที่ส่งมาด้วย — an ordered, described enclosure of a หนังสือ.

    Rendered as a numbered list on the document ("สิ่งที่ส่งมาด้วย ๑. …").
    Unlike a bare attachment, an enclosure carries an order and a caption.
    """

    _name = "sarabun.enclosure"
    _description = "Sarabun สิ่งที่ส่งมาด้วย (Enclosure)"
    _order = "sequence, id"

    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(
        default=10,
        help="The numbered-list index (๑, ๒, ๓ …).",
    )
    description = fields.Char(
        string="Description",
        required=True,
        help="Caption shown in the สิ่งที่ส่งมาด้วย list.",
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="File",
        help="Optional file for this enclosure.",
    )
