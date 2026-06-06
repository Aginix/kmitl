# -*- coding: utf-8 -*-
"""sarabun.routing.step — the single unified Route entity (ADR-0001).

One row = target (who acts) + verb (what they must do) + state + outcome
(who acted, when, the เกษียน note, the capacity signed in). It replaces the old
``routing.line`` (plan) / ``document.recipient`` (tracker) split, so there is
nothing to keep in sync and steps can be inserted mid-flow (เกษียนสั่งการ).

The engine is token-ready: every move funnels through ``act_on_step`` so a
phase-2 magic-link controller can drive the same path. Holder resolution and
notification (mail.activity) are wired here but the notification body itself is a
P4 concern (stubbed). Numbering (P3) and freeze/sign (P5) live on the document.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Keep in sync with sarabun_route_template.py
VERB_SELECTION = [
    ("acknowledge", "รับทราบ (Acknowledge)"),
    ("endorse", "เห็นชอบ (Endorse)"),
    ("sign_approve", "ลงนาม-อนุมัติ (Sign/Approve)"),
]
TARGET_MODE = [
    ("position", "Position (ตำแหน่ง)"),
    ("person", "Person (บุคคล)"),
    ("unit", "Unit (สารบรรณกลาง)"),
]
# Ranking for the document's strongest_verb_done (Recall guard, ADR-0002).
VERB_RANK = {"acknowledge": 1, "endorse": 2, "sign_approve": 3}

GATING_VERBS = ("endorse", "sign_approve")
POSITIVE_DISPOSITIONS = ("complete", "direct")


class SarabunRoutingStep(models.Model):
    _name = "sarabun.routing.step"
    _description = "Sarabun Routing Step"
    _order = "order, id"
    _inherit = ["mail.thread"]

    document_id = fields.Many2one(
        "sarabun.document", required=True, ondelete="cascade", index=True
    )
    order = fields.Integer(
        string="Stage", default=10,
        help="Steps sharing one order form a Stage and run in parallel.",
    )

    # === Verb ===
    verb = fields.Selection(VERB_SELECTION, required=True, default="endorse", tracking=True)
    for_info = fields.Boolean(
        string="สำเนาเรียน (CC)",
        help="A non-gating acknowledge step (CC). Never blocks advancement/completion.",
    )
    gating = fields.Boolean(compute="_compute_gating", store=True)

    # === Target (exactly one mode) ===
    target_mode = fields.Selection(TARGET_MODE, required=True, default="position")
    position_id = fields.Many2one("sarabun.position", string="Position")
    user_id = fields.Many2one("res.users", string="User")
    department_id = fields.Many2one("hr.department", string="Unit")
    target_name = fields.Char(compute="_compute_target_name", store=True, string="Target")

    # === Resolved holders (snapshot at activation — ADR-0003) ===
    actor_user_ids = fields.Many2many(
        "res.users",
        relation="sarabun_step_actor_rel",
        column1="step_id",
        column2="user_id",
        string="Actors (snapshot)",
        readonly=True,
        help="Resolved holder-set, written when the step becomes active. "
        "Multi-holder = first-to-act-wins. Never recomputed after activation.",
    )

    # === State ===
    state = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("active", "Active"),
            ("done", "Done"),
            ("skipped", "Skipped"),
        ],
        default="waiting",
        required=True,
        tracking=True,
        index=True,
    )

    # === Outcome ===
    disposition = fields.Selection(
        [
            ("complete", "Complete"),
            ("direct", "เกษียนสั่งการ (Direct)"),
            ("delegate", "มอบหมาย (Delegate)"),
            ("return", "ตีกลับ (Return)"),
            ("reject", "ปฏิเสธ (Reject)"),
        ],
        readonly=True,
    )
    acted_by_id = fields.Many2one("res.users", string="Acted By", readonly=True)
    acted_date = fields.Datetime(readonly=True)
    signed_as_position_id = fields.Many2one(
        "sarabun.position", string="Signed As (Capacity)", readonly=True,
        help="Capacity signed in — validated against the step's target Position (ADR-0003).",
    )
    note = fields.Text(string="เกษียน (Note)")
    delegated_to_id = fields.Many2one("res.users", string="Delegated To", readonly=True)

    # === Provenance ===
    created_by_disposition = fields.Selection(
        [("seed", "Seed"), ("direct", "Direct"), ("delegate", "Delegate"), ("return", "Return")],
        default="seed", readonly=True,
    )
    inserted_by_step_id = fields.Many2one("sarabun.routing.step", readonly=True)
    seeded_from_template_line_id = fields.Many2one("sarabun.route.template.line", readonly=True)

    # === Attempt / history (re-send freezes prior attempts; ADR-0002 §3.4) ===
    active = fields.Boolean(default=True)
    attempt_seq = fields.Integer(default=1, readonly=True)

    # === Phase-2 magic-link seam (never generated in v1) ===
    act_token = fields.Char(index=True, copy=False, groups="agx_sarabun.group_sarabun_manager")

    # === Related (display) ===
    document_state = fields.Selection(related="document_id.state", string="Document Status")

    # ------------------------------------------------------------------ computes
    @api.depends("verb", "for_info")
    def _compute_gating(self):
        for step in self:
            step.gating = step.verb in GATING_VERBS and not step.for_info

    @api.depends("target_mode", "position_id", "user_id", "department_id")
    def _compute_target_name(self):
        for step in self:
            if step.target_mode == "position":
                step.target_name = step.position_id.display_name
            elif step.target_mode == "person":
                step.target_name = step.user_id.display_name
            elif step.target_mode == "unit":
                step.target_name = step.department_id.display_name
            else:
                step.target_name = False

    # ------------------------------------------------------------- activation
    def _snapshot_holders(self):
        """Resolve the target to its current person-set and snapshot it."""
        self.ensure_one()
        if self.target_mode == "position" and self.position_id:
            users = self.position_id._current_holder_users()
        elif self.target_mode == "unit" and self.department_id:
            users = self.department_id._saraban_central_users()
        elif self.target_mode == "person" and self.user_id:
            users = self.user_id
        else:
            users = self.env["res.users"]
        self.actor_user_ids = [(6, 0, users.ids)]

    def _activate(self):
        """Make a waiting step active: snapshot holders + notify (P4)."""
        for step in self:
            step.state = "active"
            step._snapshot_holders()
            step._notify_activation()

    def _notify_activation(self):
        """Hook: schedule mail.activity for each holder + bus push.

        Implemented in P4 (notifications). v1 no-op so the engine runs headless.
        """
        return

    def _clear_activities(self):
        """Hook: clear sibling holders' activities on first-to-act (P4)."""
        return

    # ----------------------------------------------------------------- acting
    def _check_act_authority(self, actor):
        self.ensure_one()
        if actor not in self.actor_user_ids:
            raise UserError(_("You are not authorized to act on this step."))

    def act_on_step(self, disposition, vals=None, *, actor=None, token=None):
        """The single, token-ready entry point for all five dispositions.

        ``token`` is the phase-2 magic-link seam (ignored in v1; acting is by the
        logged-in user). Origin callbacks fire in this same transaction; a failing
        callback rolls the whole action back (ADR-0004) — no try/except swallow.
        """
        self.ensure_one()
        vals = vals or {}
        actor = actor or self.env.user
        if self.state != "active":
            raise UserError(_("This step is not active."))
        if self.document_id.state != "circulating":
            raise UserError(_("The document is not circulating."))
        self._check_act_authority(actor)

        note = vals.get("note")
        if disposition == "complete":
            self._do_complete(actor, note, vals.get("signed_as_position_id"))
        elif disposition == "direct":
            self._do_direct(actor, note, vals)
        elif disposition == "delegate":
            self._do_delegate(actor, note, vals)
        elif disposition == "return":
            self._do_return(actor, note, vals)
        elif disposition == "reject":
            self._do_reject(actor, note)
        else:
            raise UserError(_("Unknown disposition: %s") % disposition)

        # Generic per-step origin callback (same transaction — ADR-0004).
        self.document_id._call_origin("_on_sarabun_step", self, disposition)
        return True

    # --------------------------------------------------------- disposition core
    def _stamp(self, actor, note, disposition, signed_as_position=False):
        self.write({
            "state": "done",
            "disposition": disposition,
            "acted_by_id": actor.id,
            "acted_date": fields.Datetime.now(),
            "note": note or self.note,
            "signed_as_position_id": signed_as_position and signed_as_position.id or False,
        })
        self._clear_activities()

    def _resolve_capacity(self, signed_as_position_id):
        """Validate/derive the capacity for a sign_approve step (ADR-0003)."""
        self.ensure_one()
        if self.verb != "sign_approve":
            return self.env["sarabun.position"]
        capacity = self.env["sarabun.position"].browse(signed_as_position_id) if signed_as_position_id else self.position_id
        # In Position mode you sign in the step's capacity (acting capacity = phase-2).
        if self.position_id and capacity != self.position_id:
            raise UserError(_(
                "You must sign in the capacity the step targets (%s)."
            ) % self.position_id.display_name)
        return capacity

    def _do_complete(self, actor, note, signed_as_position_id=False):
        capacity = self._resolve_capacity(signed_as_position_id)
        self._stamp(actor, note, "complete", capacity)
        self.document_id._advance_stage()

    def _do_direct(self, actor, note, vals):
        self._stamp(actor, note, "direct")
        insert_order = self.order + 1
        self.document_id._shift_stages_from(insert_order)
        self.env["sarabun.routing.step"].create({
            "document_id": self.document_id.id,
            "order": insert_order,
            "inserted_by_step_id": self.id,
            "created_by_disposition": "direct",
            "attempt_seq": self.document_id.attempt_seq,
            "state": "waiting",
            "verb": vals.get("verb", "endorse"),
            "for_info": vals.get("for_info", False),
            "target_mode": vals.get("target_mode", "position"),
            "position_id": vals.get("position_id", False),
            "user_id": vals.get("user_id", False),
            "department_id": vals.get("department_id", False),
        })
        self.document_id._advance_stage()

    def _do_delegate(self, actor, note, vals):
        # Reassign THIS step to a new target; it stays active (Delegate ≠ Direct).
        self.write({
            "disposition": "delegate",
            "delegated_to_id": vals.get("user_id") or False,
            "note": (self.note or "") + (("\n" + note) if note else ""),
            "target_mode": vals.get("target_mode", self.target_mode),
            "position_id": vals.get("position_id", self.position_id.id),
            "user_id": vals.get("user_id", self.user_id.id),
            "department_id": vals.get("department_id", self.department_id.id),
        })
        self._snapshot_holders()
        self._notify_activation()

    def _do_return(self, actor, note, vals):
        self._stamp(actor, note, "return")
        self.document_id._do_return(
            self,
            destination=vals.get("destination", "sender_restart"),
            resume_step_id=vals.get("resume_step_id"),
        )

    def _do_reject(self, actor, note):
        self._stamp(actor, note, "reject")
        self.document_id._do_reject(self)
