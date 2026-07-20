# -*- coding: utf-8 -*-
"""sarabun.verb — the routing action (การดำเนินการ) as configurable master data.

What a routing step asks its holder to DO (รับทราบ / เห็นชอบ / ลงนาม-อนุมัติ …).
Admins may add/relabel verbs. The built-in verbs ship as noupdate data
(data/sarabun_verb_data.xml) so the engine and external callers can reference them
by **xmlid** (e.g. ``agx_sarabun.verb_sign_approve``); behaviour is driven by the
flags below, not by any identity string. The behaviour model (rank / gating /
show_signature / is_signature) is provisional — a candidate simplification is to
derive completion from the route order instead of per-verb flags; revisit after
real use.
"""
from odoo import api, fields, models


class SarabunVerb(models.Model):
    _name = "sarabun.verb"
    _description = "Sarabun Routing Verb (การดำเนินการ)"
    _order = "rank, sequence, id"

    name = fields.Char(string="Verb", required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    rank = fields.Integer(
        default=0,
        help="Strength ordering for the Recall guard (strongest verb done). "
        "Higher = stronger; ลงนาม-อนุมัติ is the strongest.",
    )
    gating = fields.Boolean(
        string="Gating",
        help="A gating verb must be positively completed for its Stage to pass. "
        "Non-gating verbs (e.g. รับทราบ) never block advancement.",
    )
    show_signature = fields.Boolean(
        string="แสดงลายเซ็น (Show signature)",
        help="Render a signature block (image + name + position + date + note) on the "
        "official document. Independent of gating; non-signing verbs (ตรวจสอบ / พิจารณา "
        "/ ส่งต่อ, a non-signing ผู้จัดทำ) leave no mark on the letter. An authoritative "
        "sign (is_signature) always shows — ADR-0008.",
    )
    is_signature = fields.Boolean(
        string="ลายเซ็นเชิงอำนาจ (Authoritative sign)",
        help="Marks ลงนาม-อนุมัติ — the authoritative approval-sign: drives capacity "
        "validation and the Recall guard (a signed document cannot be recalled). "
        "Implies แสดงลายเซ็น (ADR-0008); does not by itself gate the chain.",
    )

    @api.onchange("is_signature")
    def _onchange_is_signature(self):
        # Invariant (ADR-0008): an authoritative approval-sign always renders.
        if self.is_signature:
            self.show_signature = True
