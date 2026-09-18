# -*- coding: utf-8 -*-
from odoo import api, fields, models

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
    allow_manual = fields.Boolean(
        string="สร้างด้วยตนเองได้ (Allow Manual Creation)",
        compute="_compute_allow_manual",
        store=True,
        readonly=False,
        help="Whether a user may compose a หนังสือ of this type by hand from the "
        "Documents form. Defaults from the kind — a from_record type must be spawned "
        "by its origin record (OFF), while memo / circular are hand-composed (ON) — "
        "but is overridable, so an admin can retire a composed type from manual use "
        "without changing its kind. Off-types are hidden from the manual-create type "
        "dropdown and refused a manual (origin-less) หนังสือ (see sarabun.document).",
    )

    @api.depends("kind")
    def _compute_allow_manual(self):
        """Default manual-creatability from the kind: only from_record is origin-only.
        Editable (readonly=False), so an admin override survives — until the kind
        itself is changed, which legitimately re-derives the default."""
        for record in self:
            record.allow_manual = record.kind != "from_record"

    # Seed route (P2). Numbering sequence (P3) is added in its phase; report
    # template binding (P5) lives in agx_sarabun_layout's report_template_id.
    default_route_id = fields.Many2one(
        comodel_name="sarabun.route.template",
        string="Default Route",
        help="Seed template materialised into routing steps at send (ADR-0001).",
    )
    # sequence_id = fields.Many2one("sarabun.document.sequence")      # P3 register
