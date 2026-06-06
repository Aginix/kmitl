# -*- coding: utf-8 -*-
from odoo import fields, models

# === Document kind — the fixed, dev-extensible behaviour axis ===
# A หนังสือ's kind drives its report template, numbering and routing rules.
# It is kept SEPARATE from the admin-configurable type record (the old code
# wrongly used a single hardcoded ``code`` Selection as both behaviour key and
# identifier). Dependent modules may extend this list; phase-2 adds
# ``external`` (หนังสือภายนอก), ``order`` (คำสั่ง), ``announcement`` (ประกาศ).
KIND_SELECTION = [
    ("memo", "บันทึกข้อความ (Internal Memo)"),
    ("circular", "หนังสือเวียน (Circular)"),
    ("from_record", "จากระบบงาน (From Record)"),
]


class SarabunDocumentType(models.Model):
    """Admin-configurable concrete document type (e.g. "บันทึกข้อความกองคลัง").

    The configurable layer above the fixed ``kind`` axis. Each type binds a
    register sequence (P3), a default seed route (P2) and a report template (P5)
    and points at exactly one ``kind``.
    """

    _name = "sarabun.document.type"
    _description = "Sarabun Document Type"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, translate=True)
    kind = fields.Selection(
        selection=KIND_SELECTION,
        string="Kind",
        required=True,
        default="from_record",
        help="The fixed behaviour axis. v1 emphasis is from_record (origin-driven e-flow).",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    description = fields.Text(string="Description")

    # Seed route (P2). Numbering sequence (P3) and report template (P5) bindings
    # are added in their phases.
    default_route_id = fields.Many2one(
        comodel_name="sarabun.route.template",
        string="Default Route",
        help="Seed template materialised into routing steps at send (ADR-0001).",
    )
    # sequence_id = fields.Many2one("sarabun.document.sequence")      # P3 register
    # report_template_id = fields.Many2one("ir.actions.report")       # P5 cover sheet
