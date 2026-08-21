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
TARGET_MODE = [
    ("unit", "ธุรการหน่วยงาน (Unit Clerk)"),
    ("person", "บุคลากร (Personnel)"),
    ("position", "ตำแหน่ง (Position)"),
]
# Verb strength/gating/signature now live on sarabun.verb records (master data);
# the engine reads verb.rank / verb.gating / verb.is_signature. Only the
# disposition axis remains a fixed Selection.
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
        string="Stage", default=1,
        help="Steps sharing one order form a Stage and run in parallel.",
    )

    # === Verb (การดำเนินการ — configurable master data) ===
    verb = fields.Many2one(
        "sarabun.verb",
        string="Verb",
        required=True,
        ondelete="restrict",
        tracking=True,
        help="No default on purpose — the user must read the choices and pick the "
        "การดำเนินการ deliberately, so a step is never sent with an unintended verb.",
    )
    for_info = fields.Boolean(
        string="สำเนาเรียน (CC)",
        help="A non-gating acknowledge step (CC). Never blocks advancement/completion.",
    )
    gating = fields.Boolean(compute="_compute_gating", store=True)

    # === Target (exactly one mode) — configured against HR personnel ===
    target_mode = fields.Selection(TARGET_MODE, required=True, default="position")
    position_id = fields.Many2one("sarabun.position", string="Position")
    employee_id = fields.Many2one("hr.employee", string="บุคลากร (Person)")
    department_id = fields.Many2one(
        "hr.department", string="Unit",
        domain=[("is_sarabun_office", "=", True)],
        help="เป้าหมายแบบ ธุรการหน่วยงาน — เลือกได้เฉพาะหน่วยงานที่ตั้งเป็นหน่วยงานธุรการ.",
    )
    target_name = fields.Char(compute="_compute_target_name", store=True, string="Target")
    preview_holder_ids = fields.Many2many(
        "hr.employee",
        compute="_compute_preview_holders",
        string="ผู้ดำเนินการปัจจุบัน (Current Holders)",
        help="Who would act on this step right now — the position's holder(s) or the "
        "unit's ธุรการหน่วยงาน. May be more than one (first-to-act). This is a live "
        "preview; the actual actors are snapshotted when the step activates.",
    )
    activated_date = fields.Datetime(
        string="วันที่ได้รับ (Activated)",
        readonly=True,
        copy=False,
        help="When this step became active — the moment its recipients received it.",
    )
    recipient_ids = fields.One2many(
        "sarabun.step.recipient",
        "step_id",
        string="Recipients (per-person read tracking)",
        copy=False,
    )

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
    acted_date = fields.Datetime(string="วันที่ลงนาม/ดำเนินการ", readonly=True)
    signed_as_position_id = fields.Many2one(
        "sarabun.position", string="Signed As (Capacity)", readonly=True,
        help="Capacity signed in — validated against the step's target Position (ADR-0003).",
    )
    note = fields.Text(string="เกษียน (Note)")
    delegated_to_id = fields.Many2one("hr.employee", string="Delegated To", readonly=True)

    # === Signature snapshot (frozen at signing — ADR-0009) ===
    # ชื่อ / ตำแหน่ง / ลายเซ็น captured the instant this step is signed, so later edits
    # to the HR name, the sarabun.position name, or the employee's signature image
    # never rewrite an already-signed หนังสือ (extends ADR-0003's holder snapshot from
    # routing resolution to the rendered block). Written only for show_signature verbs;
    # the endorsement block reads these first and falls back to live master data for
    # legacy / in-flight rows.
    signed_name = fields.Char(string="ชื่อผู้ลงนาม (snapshot)", readonly=True, copy=False)
    signed_position_name = fields.Char(
        string="ตำแหน่งที่ลงนาม (snapshot)", readonly=True, copy=False
    )
    signed_signature = fields.Binary(
        string="ลายเซ็น (snapshot)", attachment=True, readonly=True, copy=False
    )

    # === Timeline (per-step routing timing) ===
    # วันที่ได้รับ = activated_date (above). วันที่ลงนาม = acted_date (above).
    read_date = fields.Datetime(
        string="วันที่อ่าน",
        compute="_compute_read_date",
        store=True,
        help="When this step was first opened — the earliest recipient read.",
    )
    sent_date = fields.Datetime(
        string="วันที่ส่ง",
        readonly=True,
        copy=False,
        help="Stamped when the step is acted/forwarded (ส่งต่อ). In v1 acting "
        "auto-sends, so it equals วันที่ลงนาม; a future sign-then-manual-send sets it "
        "separately.",
    )
    processing_duration = fields.Float(
        string="ระยะเวลาดำเนินการ",
        compute="_compute_processing_duration",
        store=True,
        help="Hours from วันที่ได้รับ (activated) to max(วันที่ส่ง, วันที่ลงนาม).",
    )

    # === Provenance ===
    created_by_disposition = fields.Selection(
        [("seed", "Seed"), ("direct", "Direct"), ("delegate", "Delegate"), ("return", "Return")],
        default="seed", readonly=True,
    )
    inserted_by_step_id = fields.Many2one("sarabun.routing.step", readonly=True)
    seeded_from_template_line_id = fields.Many2one("sarabun.route.template.line", readonly=True)

    # === Originator (ผู้จัดทำ/ผู้ส่ง) — the mandatory, locked first step ===
    is_originator = fields.Boolean(
        default=False,
        copy=False,
        readonly=True,
        help="The mandatory first step = the ผู้จัดทำ/ผู้ส่ง, auto-signed at send. "
        "Cannot be deleted, and only its verb may be changed; excluded from "
        "has_signed / strongest_verb (an originator signature is not an approval).",
    )

    # === Attempt / history (re-send freezes prior attempts; ADR-0002 §3.4) ===
    active = fields.Boolean(default=True)
    attempt_seq = fields.Integer(default=1, readonly=True)

    # === Phase-2 magic-link seam (never generated in v1) ===
    act_token = fields.Char(index=True, copy=False, groups="agx_sarabun.group_sarabun_manager")

    # === Related (display) ===
    document_state = fields.Selection(related="document_id.state", string="Document Status")

    # ------------------------------------------------------------------ defaults
    @api.model
    def _default_verb(self):
        return self.env.ref("agx_sarabun.verb_endorse", raise_if_not_found=False)

    @api.onchange("document_id")
    def _onchange_document_default_order(self):
        """Auto-increment ลำดับ (Stage) for a freshly added step.

        The modal's "บันทึกและสร้างใหม่" (Save & New) strips every ``default_*`` from
        the context before opening the next record (Odoo web form_view_dialog), so a
        context-fed ``default_order`` cannot survive past the 1st record — the 2nd, 3rd…
        would all fall back to 1 and silently collide on the same Stage. Deriving the
        order from the sibling steps here makes every fresh step land on the next free
        Stage no matter how it was added. The originator is fixed and never re-numbered;
        the user may still set two steps to the same order for a parallel Stage."""
        for step in self:
            if step.is_originator:
                continue
            orders = (step.document_id.routing_step_ids - step).mapped("order")
            step.order = (max(orders) + 1) if orders else 1

    # ------------------------------------------------------------ ORM guards
    def write(self, vals):
        """The originator (ผู้จัดทำ/ผู้ส่ง) row is locked — a user may change only its
        verb. Engine writes (sudo: activation, archive, stamping) pass through."""
        if not self.env.su and vals and set(vals) - {"verb"}:
            if self.filtered("is_originator"):
                raise UserError(_(
                    "The ผู้จัดทำ/ผู้ส่ง step is fixed — only its การดำเนินการ (verb) "
                    "may be changed."
                ))
        return super().write(vals)

    def unlink(self):
        """A user cannot remove the originator row (it must always be the first step).
        Document deletion cascades at the DB level (ondelete='cascade'), bypassing
        the ORM unlink, so it is not blocked here."""
        if not self.env.su and self.filtered("is_originator"):
            raise UserError(_(
                "The ผู้จัดทำ/ผู้ส่ง step cannot be removed from the Route."
            ))
        return super().unlink()

    # ------------------------------------------------------------------ computes
    @api.depends("verb.gating", "for_info")
    def _compute_gating(self):
        for step in self:
            step.gating = step.verb.gating and not step.for_info

    @api.depends("target_mode", "position_id", "employee_id", "department_id")
    def _compute_target_name(self):
        for step in self:
            if step.target_mode == "position":
                step.target_name = step.position_id.display_name
            elif step.target_mode == "person":
                step.target_name = step.employee_id.display_name
            elif step.target_mode == "unit":
                step.target_name = step.department_id.display_name
            else:
                step.target_name = False

    @api.depends("target_mode", "position_id", "department_id", "employee_id")
    def _compute_preview_holders(self):
        for step in self:
            if step.target_mode == "position" and step.position_id:
                step.preview_holder_ids = step.position_id._current_holder_employees()
            elif step.target_mode == "unit" and step.department_id:
                step.preview_holder_ids = step.department_id._saraban_central_employees()
            elif step.target_mode == "person" and step.employee_id:
                step.preview_holder_ids = step.employee_id
            else:
                step.preview_holder_ids = False

    @api.depends("recipient_ids.read_date")
    def _compute_read_date(self):
        for step in self:
            reads = [d for d in step.recipient_ids.mapped("read_date") if d]
            step.read_date = min(reads) if reads else False

    @api.depends("activated_date", "sent_date", "acted_date")
    def _compute_processing_duration(self):
        """Hours from received (activated_date) to max(sent_date, acted_date)."""
        for step in self:
            start = step.activated_date
            ends = [d for d in (step.sent_date, step.acted_date) if d]
            if start and ends:
                step.processing_duration = (max(ends) - start).total_seconds() / 3600.0
            else:
                step.processing_duration = 0.0

    # ------------------------------------------------------------- activation
    def _snapshot_holders(self):
        """Resolve the target to its current person-set (res.users) and snapshot it.
        Targets are configured as hr.employee; the engine acts by logged-in user, so
        we snapshot the employees' linked users (personnel with no user cannot act)."""
        self.ensure_one()
        if self.target_mode == "position" and self.position_id:
            users = self.position_id._current_holder_users()
        elif self.target_mode == "unit" and self.department_id:
            users = self.department_id._saraban_central_users()
        elif self.target_mode == "person" and self.employee_id:
            users = self.employee_id.user_id
        else:
            users = self.env["res.users"]
        self.actor_user_ids = [(6, 0, users.ids)]
        self._sync_recipients(users)

    def _sync_recipients(self, users):
        """Materialise one sarabun.step.recipient per snapshot holder (per-person
        route + read tracking). Idempotent: only adds rows for new users. Recipients
        are engine-owned (users have read-only access), so create via sudo."""
        self.ensure_one()
        Recipient = self.env["sarabun.step.recipient"].sudo()
        existing = self.recipient_ids.mapped("user_id")
        now = fields.Datetime.now()
        for user in users - existing:
            Recipient.create({
                "step_id": self.id,
                "user_id": user.id,
                "received_date": now,
            })

    def _activate(self):
        """Make a waiting step active: snapshot holders + schedule activities."""
        for step in self:
            step.state = "active"
            step.activated_date = fields.Datetime.now()
            step._snapshot_holders()
        self._schedule_activities()

    def _activity_summary(self):
        self.ensure_one()
        return self.verb.name

    def _activity_type_xmlid(self):
        """The awaiting-action activity type for this step (ADR-0014): EXECUTION iff
        the step gates or physically signs the letter (``gating`` OR
        ``show_signature`` — so รับทราบและลงนาม is execution, a signature can't be
        Mark-as-Read'd away), else ACKNOWLEDGEMENT (a pure read-only รับทราบ)."""
        self.ensure_one()
        if self.gating or self.verb.show_signature:
            return "agx_sarabun.mail_activity_sarabun_action"
        return "agx_sarabun.mail_activity_sarabun_ack"

    def _schedule_activities(self):
        """One awaiting-action mail.activity per snapshot holder of each ACTIVE step
        — gating AND non-gating (รับทราบ / สำเนาเรียน / รับทราบและลงนาม) alike
        (ADR-0014); the old gating-only filter is gone so no awaiting-action work is
        invisible once the systray is dissolved. The type is picked per step by
        ``_activity_type_xmlid`` (execution vs acknowledgement). Base e-Saraban
        stands on native mail.activity; the agx_sarabun_todo bridge tags the types
        with ``todo_category`` to route them into the unified Todo inbox.

        The step↔activity Link is engine-owned bookkeeping (like the recipient
        rows): created via sudo so a plain sender/actor needs no write on it."""
        Link = self.env["sarabun.routing.step.activity"].sudo()
        for step in self.filtered(lambda s: s.state == "active"):
            xmlid = step._activity_type_xmlid()
            if not self.env.ref(xmlid, raise_if_not_found=False):
                continue
            doc = step.document_id
            for usr in step.actor_user_ids:
                act = doc.activity_schedule(
                    act_type_xmlid=xmlid,
                    summary=step._activity_summary(),
                    user_id=usr.id,
                )
                if act:
                    Link.create({"step_id": step.id, "activity_id": act.id, "user_id": usr.id})

    def _clear_activities(self):
        """Clear every awaiting-action activity tied to these steps (all holders) —
        first-to-act and on every lifecycle close (§7.2). Kept in core: the reset
        add-on (agx_sarabun_reset) depends on it."""
        # sudo: the to-dos being cleared belong to the OTHER actors (mail.activity's
        # ir.rule only lets a user unlink their own / self-created ones), and clearing
        # them is an engine operation — e.g. the sender's ดึงกลับ drops the approvers'
        # pending activities.
        links = self.env["sarabun.routing.step.activity"].sudo().search(
            [("step_id", "in", self.ids)]
        )
        links.mapped("activity_id").unlink()
        links.unlink()

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
        # ตีกลับ / ปฏิเสธ are gating-actor moves only (ADR-0006): a รับทราบ / CC
        # recipient may only acknowledge (complete), never return or reject.
        if disposition in ("return", "reject") and not self.gating:
            raise UserError(_(
                "Only the actor of a gating step (เห็นชอบ / ลงนาม-อนุมัติ) may "
                "ตีกลับ (return) or ปฏิเสธ (reject)."
            ))

        # Authority is verified above. The lifecycle transition itself — stamping the
        # step and driving the document's state / register / freeze — is a SYSTEM
        # operation, so it runs privileged: a non-sender approver may complete / return
        # / reject without holding document-write rights (the write ACL is sender +
        # manager only). The acting user is recorded via ``actor`` (acted_by_id), not
        # env.user, so the audit trail is unchanged.
        step = self.sudo()
        note = vals.get("note")
        if disposition == "complete":
            step._do_complete(actor, note, vals.get("signed_as_position_id"))
        elif disposition == "direct":
            step._do_direct(actor, note, vals)
        elif disposition == "delegate":
            step._do_delegate(actor, note, vals)
        elif disposition == "return":
            step._do_return(actor, note, vals)
        elif disposition == "reject":
            step._do_reject(actor, note)
        else:
            raise UserError(_("Unknown disposition: %s") % disposition)

        # Generic per-step origin callback (same transaction — ADR-0004).
        step.document_id._call_origin("_on_sarabun_step", self, disposition)
        return True

    # --------------------------------------------------------- disposition core
    def _stamp(self, actor, note, disposition, signed_as_position=False):
        now = fields.Datetime.now()
        vals = {
            "state": "done",
            "disposition": disposition,
            "acted_by_id": actor.id,
            "acted_date": now,
            "note": note or self.note,
            "signed_as_position_id": signed_as_position and signed_as_position.id or False,
        }
        # v1: a positive action auto-sends the หนังสือ onward, so วันที่ส่ง = วันที่ลงนาม
        # (a future sign-then-manual-send would stamp sent_date separately).
        if disposition in POSITIVE_DISPOSITIONS:
            vals["sent_date"] = now
            # Freeze the signer's rendered identity at the instant of signing (ADR-0009)
            # — exactly the rows the endorsement block renders (positive-done ∧
            # show_signature); a ตีกลับ / ปฏิเสธ signs nothing.
            if self.verb.show_signature:
                vals.update(self._signature_snapshot_vals(actor, signed_as_position))
        self.write(vals)
        self._clear_activities()

    def _signature_snapshot_vals(self, actor, capacity=False):
        """Snapshot the signer's rendered identity — ชื่อ / ตำแหน่ง / ลายเซ็น — at the
        instant of signing (ADR-0009). Extends ADR-0003's holder snapshot from routing
        *resolution* to the *rendered block*: once captured, later edits to the HR name,
        the sarabun.position name, or the employee's signature image never rewrite an
        already-signed หนังสือ. Position prefers the signed capacity, else the step's
        target Position — mirroring the block's live fallback order.

        The source is read under ``sudo`` (like the rest of the _stamp transition — a
        SYSTEM stamping operation): capturing the official-record identity must not
        depend on the acting user's hr.employee read grants."""
        self.ensure_one()
        actor = actor.sudo()
        employee = actor.employee_id
        position = capacity or self.position_id
        return {
            "signed_name": employee.name or actor.name,
            "signed_position_name": position.name or "",
            "signed_signature": employee.signature or False,
        }

    def _resolve_capacity(self, signed_as_position_id):
        """Validate/derive the capacity for a sign_approve step (ADR-0003)."""
        self.ensure_one()
        if not self.verb.is_signature:
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
            "verb": vals.get("verb") or self._default_verb().id,
            "for_info": vals.get("for_info", False),
            "target_mode": vals.get("target_mode", "position"),
            "position_id": vals.get("position_id", False),
            "employee_id": vals.get("employee_id", False),
            "department_id": vals.get("department_id", False),
        })
        self.document_id._advance_stage()

    def _do_delegate(self, actor, note, vals):
        # Reassign THIS step to a new target; it stays active (Delegate ≠ Direct).
        self._clear_activities()  # drop the original holders' to-dos (§7.4)
        self.write({
            "disposition": "delegate",
            "delegated_to_id": vals.get("employee_id") or False,
            "note": (self.note or "") + (("\n" + note) if note else ""),
            "target_mode": vals.get("target_mode", self.target_mode),
            "position_id": vals.get("position_id", self.position_id.id),
            "employee_id": vals.get("employee_id", self.employee_id.id),
            "department_id": vals.get("department_id", self.department_id.id),
        })
        self._snapshot_holders()
        self._schedule_activities()  # fresh to-do for the new holder(s)

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

    def _resume_seed_vals(self):
        """Seed vals to re-create this step fresh (``waiting``) in a new attempt
        after a ตีกลับ→resume — the original step stays archived as history so the
        prior chain is never overwritten (ADR-0006)."""
        self.ensure_one()
        return {
            "order": self.order,
            "verb": self.verb.id,
            "for_info": self.for_info,
            "target_mode": self.target_mode,
            "position_id": self.position_id.id,
            "employee_id": self.employee_id.id,
            "department_id": self.department_id.id,
            "is_originator": self.is_originator,
            "state": "waiting",
        }
