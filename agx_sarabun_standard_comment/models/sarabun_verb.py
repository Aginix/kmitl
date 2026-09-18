# -*- coding: utf-8 -*-
"""Per-verb default ข้อความมาตรฐาน — pre-fills the เกษียน comment on wizard open."""
from odoo import fields, models


class SarabunVerb(models.Model):
    _inherit = "sarabun.verb"

    default_standard_comment_id = fields.Many2one(
        "sarabun.standard.comment",
        string="ข้อความมาตรฐานเริ่มต้น (Default comment)",
        help="Pre-fills the เกษียน comment when a step carrying this verb is acted on. "
        "The actor may still pick another standard comment or type freely.",
    )
