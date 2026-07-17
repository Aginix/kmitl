# -*- coding: utf-8 -*-
"""sarabun.verb — the routing action (การดำเนินการ) as configurable master data.

What a routing step asks its holder to DO (รับทราบ / เห็นชอบ / ลงนาม-อนุมัติ …).
Admins may add/relabel verbs, but the ENGINE branches on the stable ``code`` plus
the behaviour flags (``rank`` / ``gating`` / ``is_signature``) — never on the label.
The built-in verbs ship as noupdate data (data/sarabun_verb_data.xml) so both the
engine and external callers can reference them by xmlid/code (the programmable seam).
"""
from odoo import api, fields, models


class SarabunVerb(models.Model):
    _name = "sarabun.verb"
    _description = "Sarabun Routing Verb (การดำเนินการ)"
    _order = "rank, sequence, id"

    name = fields.Char(string="Verb", required=True, translate=True)
    code = fields.Char(
        string="Code",
        required=True,
        help="Stable technical key the engine branches on (e.g. 'sign_approve'). "
        "Do not change on the built-in verbs.",
    )
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

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Verb code must be unique!"),
    ]

    @api.model
    def _by_code(self, code):
        """Return the verb record for a stable ``code`` (programmable seam)."""
        return self.search([("code", "=", code)], limit=1)
