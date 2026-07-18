# -*- coding: utf-8 -*-
"""sarabun.verb — the routing action (การดำเนินการ) as configurable master data.

What a routing step asks its holder to DO (รับทราบ / เห็นชอบ / ลงนาม-อนุมัติ …).
Admins may add/relabel verbs. The built-in verbs ship as noupdate data
(data/sarabun_verb_data.xml) so the engine and external callers can reference them
by **xmlid** (e.g. ``agx_sarabun.verb_sign_approve``); behaviour is driven by the
flags below, not by any identity string. The behaviour model (rank / gating /
is_signature) is provisional — a candidate simplification is to derive completion
from the route order instead of per-verb flags; revisit after real use.
"""
from odoo import fields, models


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
    is_signature = fields.Boolean(
        string="Signing verb",
        help="Marks ลงนาม-อนุมัติ — drives the signature block, capacity validation "
        "and the Recall guard (a signed document cannot be recalled).",
    )
