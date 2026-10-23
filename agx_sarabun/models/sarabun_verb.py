"""sarabun.verb — the routing action (การดำเนินการ) as configurable master data.

What a routing step asks its holder to DO (รับทราบ / เห็นชอบ / ลงนาม-อนุมัติ …).
Admins may add/relabel verbs. The built-in verbs ship as noupdate data
(data/sarabun_verb_data.xml) so the engine and external callers can reference them
by **xmlid** (e.g. ``agx_sarabun.verb_sign_approve``); behaviour is driven by the
flags below, not by any identity string. The behaviour model (rank / gating /
show_signature / is_signature) is provisional — a candidate simplification is to
derive completion from the route order instead of per-verb flags; revisit after
real use.

Each verb owns one ``mail.activity.type`` (ADR-0020), named exactly as the verb, so
the awaiting-action Todo tells the holder what to do ("ตรวจเอกสาร") instead of a
generic "ต้องดำเนินการ". The sync is one-way verb → type (name in every language,
active, res_model); icon / decoration stay editable on the type itself.
"""

from odoo import api, fields, models

# Initial icon of a verb's activity type (ADR-0020), set once at creation: a verb
# that gates or signs gets the old _action pencil, a pure รับทราบ the old _ack eye.
ACK_ICON = "fa-eye"
ACTION_ICON = "fa-pencil-square-o"


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
    issues_number = fields.Boolean(
        string="ออกเลขที่หนังสือ (Issues number)",
        help="Completing a step with this verb runs ลงทะเบียน: the หนังสือ gets its "
        "official number at that moment (the first such step wins). Every route must "
        "contain one. Independent of the other flags, so a non-signing ธุรการ verb may "
        "issue the number too (ADR-0017).",
    )

    activity_type_id = fields.Many2one(
        "mail.activity.type",
        string="Activity Type",
        readonly=True,
        copy=False,
        ondelete="set null",
        help="The awaiting-action activity type this verb raises — created and kept "
        "in sync (name / active) automatically (ADR-0020).",
    )

    @api.model_create_multi
    def create(self, vals_list):
        verbs = super().create(vals_list)
        verbs._sync_activity_type()
        return verbs

    def write(self, vals):
        res = super().write(vals)
        if {"name", "active"} & set(vals):
            self._sync_activity_type()
        return res

    def unlink(self):
        types = self.activity_type_id.sudo()
        res = super().unlink()
        # A type an activity still points at (ondelete=restrict) is kept, archived.
        in_use = (
            self.env["mail.activity"]
            .sudo()
            .search([("activity_type_id", "in", types.ids)])
            .activity_type_id
        )
        (types - in_use).unlink()
        in_use.write({"active": False})
        return res

    def _sync_activity_type(self):
        """Create or update each verb's owned activity type (one-way, sudo — the
        type is engine bookkeeping an admin of verbs need not have rights on)."""
        Type = self.env["mail.activity.type"].sudo()
        for verb in self:
            vals = {"active": verb.active, "res_model": "sarabun.document"}
            if verb.activity_type_id:
                verb.activity_type_id.sudo().write(vals)
            else:
                acts = verb.gating or verb.show_signature
                verb.activity_type_id = Type.create(
                    dict(
                        vals,
                        name=verb.name,
                        icon=ACTION_ICON if acts else ACK_ICON,
                        category="default",
                    )
                )
        if self:
            # The name is copied with ALL its translations (jsonb) verbatim.
            self.flush_recordset(["name", "activity_type_id"])
            Type.flush_model()
            self.env.cr.execute(
                """
                UPDATE mail_activity_type t SET name = v.name
                  FROM sarabun_verb v
                 WHERE v.activity_type_id = t.id AND v.id IN %s
                """,
                [tuple(self.ids)],
            )
            self.env["mail.activity.type"].invalidate_model(["name"])

    def action_open_activity_type(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.activity.type",
            "res_id": self.activity_type_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.onchange("is_signature")
    def _onchange_is_signature(self):
        # Invariant (ADR-0008): an authoritative approval-sign always renders.
        if self.is_signature:
            self.show_signature = True
