# -*- coding: utf-8 -*-
"""sarabun.document — the หนังสือ (Document), protagonist of e-Saraban.

P1 scope: the static data foundation only (header, classification, origin link,
อ้างถึง / สิ่งที่ส่งมาด้วย, lifecycle state field). The routing engine and the
lifecycle state *machine* (transitions, numbering, freeze, callbacks) arrive in
P2–P5 — see DESIGN.md and IMPLEMENTATION-PLAN.md. Methods here are intentionally
minimal; behaviour is added per phase.
"""
import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .sarabun_routing_step import POSITIVE_DISPOSITIONS

_logger = logging.getLogger(__name__)


class SarabunDocument(models.Model):
    _name = "sarabun.document"
    _description = "Sarabun Document (หนังสือ)"
    _inherit = ["mail.thread", "mail.activity.mixin", "thai.date.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "subject"]

    # === Identification ===
    name = fields.Char(
        string="Document Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
        index="trigram",
        help="Official registered number (rendered in พ.ศ.). Assigned at send (P3); "
        "stays '/' while draft.",
    )

    # === Classification (kind / type) ===
    type_id = fields.Many2one(
        comodel_name="sarabun.document.type",
        string="Document Type",
        required=True,
        tracking=True,
    )
    kind = fields.Selection(
        related="type_id.kind",
        string="Kind",
        store=True,
        readonly=True,
    )

    # === Header (เรื่อง / เรียน / วันที่) ===
    subject = fields.Text(string="เรื่อง (Subject)", required=True, tracking=True)
    date = fields.Date(
        string="วันที่ (Document Date)",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Defaults to today at creation (auto). Kept read-only in the form for "
        "now; making it editable is a later phase.",
    )
    addressee_prefix_id = fields.Many2one(
        comodel_name="sarabun.addressee.prefix",
        string="คำขึ้นต้น (Prefix)",
        default=lambda self: self.env.ref(
            "agx_sarabun.addressee_prefix_rian", raise_if_not_found=False
        ),
        help="Salutation opening the เรียน line (เรียน / กราบทูล / เสนอ …).",
    )
    addressee = fields.Text(
        string="เรียน (Addressee)",
        tracking=True,
        help="The ceremonial recipient on the หนังสือ header — its own field, "
        "separate from the routing actors. Manual or origin-set.",
    )
    content = fields.Html(
        string="เนื้อหา (Content)",
        sanitize=True,
        help="The body of the หนังสือ. For a composed memo/circular this IS the "
        "letter body; for a from_record document it is an optional covering note "
        "rendered above the origin's report. Full regulation บันทึกข้อความ layout "
        "is phase-2 — v1 is free rich text.",
    )
    remark = fields.Html(
        string="หมายเหตุ (Remark)",
        sanitize=True,
        help="Optional internal note — not part of the letter body.",
    )

    # === Sender (ส่วนงานเจ้าของเรื่อง) ===
    sender_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Sender",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        help="Owner of the เรื่อง. Never copied — a duplicate belongs to whoever "
        "made it (falls back to the default = current user).",
    )
    sender_department_id = fields.Many2one(
        comodel_name="hr.department",
        string="ส่วนงาน (Sender Department)",
        default=lambda self: self._default_sender_department_id(),
        required=True,
        tracking=True,
        help="Owning unit — drives register resolution (ส่วนงาน × type) in P3.",
    )
    sender_suffix = fields.Char(
        string="Sender Suffix",
        help="Sub-unit name or extension (e.g. 'สำนักงานคณบดี', 'ต่อ 1234').",
    )

    # === Lifecycle (state field; the state MACHINE is P2 — ADR-0002) ===
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง (Draft)"),
            ("circulating", "กำลังดำเนินการ (Circulating)"),
            ("completed", "เสร็จสิ้น (Completed)"),
            ("returned", "ตีกลับ (Returned)"),
            ("rejected", "ปฏิเสธ (Rejected)"),
            ("cancelled", "ยกเลิก (Cancelled)"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    # === Origin link (1:N side lives here — ADR-0004) ===
    origin_model = fields.Char(string="Origin Model", readonly=True, index=True)
    origin_res_id = fields.Integer(string="Origin Record ID", readonly=True, index=True)
    origin_reference = fields.Char(
        string="Origin Reference",
        compute="_compute_origin_reference",
    )

    # === อ้างถึง (References) ===
    reference_document_ids = fields.Many2many(
        comodel_name="sarabun.document",
        relation="sarabun_document_reference_rel",
        column1="document_id",
        column2="referenced_id",
        string="อ้างถึง (Documents)",
        help="Prior in-system หนังสือ referenced by this one.",
    )
    reference_line_ids = fields.One2many(
        comodel_name="sarabun.reference.line",
        inverse_name="document_id",
        string="อ้างถึง (External)",
        help="Free-text references to letters outside the system.",
    )

    # === สิ่งที่ส่งมาด้วย (Enclosures) ===
    enclosure_ids = fields.One2many(
        comodel_name="sarabun.enclosure",
        inverse_name="document_id",
        string="สิ่งที่ส่งมาด้วย (Enclosures)",
    )

    # === Routing (the living Route — ADR-0001) ===
    route_template_id = fields.Many2one(
        comodel_name="sarabun.route.template",
        string="Route Template (seed)",
        help="Optional template that seeds the steps at send. Not authoritative "
        "once seeded — the Route lives on the document.",
    )
    routing_step_ids = fields.One2many(
        comodel_name="sarabun.routing.step",
        inverse_name="document_id",
        string="Routing",
        domain=[("active", "=", True)],
        copy=False,
        help="The living Route — current attempt's steps.",
    )
    archived_step_ids = fields.One2many(
        comodel_name="sarabun.routing.step",
        inverse_name="document_id",
        string="Routing History",
        domain=[("active", "=", False)],
        copy=False,
        help="Frozen steps of closed attempts (kept for the เกษียน trail).",
    )
    attempt_seq = fields.Integer(
        string="Attempt",
        default=1,
        readonly=True,
        copy=False,
        help="Generation counter bumped on each re-send so prior attempts survive "
        "as history (ADR-0002 §3.4).",
    )
    strongest_verb_id = fields.Many2one(
        comodel_name="sarabun.verb",
        string="Strongest Verb Done",
        compute="_compute_strongest_verb_done",
        store=True,
        help="Highest-ranked verb positively completed so far. Drives the Recall "
        "window (Recall blocked once a signing step has occurred — ADR-0002).",
    )
    has_signed = fields.Boolean(compute="_compute_strongest_verb_done", store=True)
    can_withdraw = fields.Boolean(
        compute="_compute_can_withdraw",
        string="Can Withdraw",
        help="True only for the sender (or a manager) while the หนังสือ may still be "
        "ดึงกลับ / ยกเลิกการส่ง — mirrors _check_sender_withdraw_allowed so a mere "
        "recipient never sees the withdraw button.",
    )

    # current user's actionable step(s) + routing progress (UI)
    my_active_step_id = fields.Many2one(
        comodel_name="sarabun.routing.step",
        compute="_compute_my_active_step",
        string="My Pending Step",
        help="The current user's *active* step (drives the 'Act on My Step' button). "
        "Empty once they have acted.",
    )
    my_reaching_step_id = fields.Many2one(
        comodel_name="sarabun.routing.step",
        compute="_compute_my_active_step",
        string="Step That Reached Me",
        help="The step by which this หนังสือ reached the current user — their active "
        "step, or (once they have acted) their most recent completed step. Backs the "
        "incoming-box columns (read status / received / verb) so they stay populated "
        "after the user has acted.",
    )
    pending_ack_count = fields.Integer(
        compute="_compute_routing_progress", string="ค้างรับทราบ",
    )
    routing_progress = fields.Float(
        compute="_compute_routing_progress", string="Routing Progress",
    )

    # === Inbox (per current user — from the step that reached them) ===
    my_received_date = fields.Datetime(
        compute="_compute_my_inbox", string="วันที่ได้รับ",
        help="When the step that reached the current user was received by them "
        "(per-person; may differ from the step's activation under delegation).",
    )
    my_action_verb_id = fields.Many2one(
        "sarabun.verb", compute="_compute_my_inbox", string="เพื่อดำเนินการ",
        help="What the current user was asked to do on the step that reached them "
        "(may already be a completed step).",
    )
    my_read_state = fields.Selection(
        selection=[
            ("unread", "รอการเปิดอ่าน"),
            ("read", "เปิดอ่านแล้ว"),
            ("forwarded", "รอการส่งต่อ"),
        ],
        compute="_compute_my_inbox", string="สถานะการอ่าน",
        help="Whether the current user has opened this หนังสือ — tracked per person.",
    )

    # === Numbering / Register (P3 — ADR-0002 §4) ===
    register_number_id = fields.Many2one(
        comodel_name="sarabun.document.number",
        string="Register Number",
        readonly=True,
        copy=False,
        help="The register ledger row assigned by ลงทะเบียน at send.",
    )
    numbering_mode = fields.Selection(
        selection=[
            ("auto", "Auto (next available)"),
            ("reserved", "Reserved number"),
            ("gap", "Fill a gap"),
            ("manual", "Manual"),
        ],
        string="Numbering Mode",
        default="auto",
        help="from_record always registers automatically; reserved/gap/manual are "
        "for manual compose (memo/circular).",
    )
    manual_counter = fields.Integer(
        string="Manual Number",
        help="The counter to use in manual/gap mode (routed through the same "
        "atomic allocation + unique backstop).",
    )
    reserved_number_id = fields.Many2one(
        comodel_name="sarabun.document.number",
        string="Reserved Number",
        domain="[('state', '=', 'reserved')]",
    )

    # === Signing / official record (P5 — DESIGN §5) ===
    signed_pdf = fields.Binary(
        string="ฉบับลงนาม (Signed Copy)", attachment=True, copy=False, readonly=True,
        help="Immutable PDF frozen at completion (cover sheet + origin body merged).",
    )
    signed_pdf_filename = fields.Char(copy=False, readonly=True)
    signed_at = fields.Datetime(string="Frozen At", copy=False, readonly=True)
    is_frozen = fields.Boolean(compute="_compute_is_frozen")

    # === Attachments ===
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[("res_model", "=", "sarabun.document")],
        string="Attachments",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # === Semantic helpers (computed booleans — accessed as attributes) ===
    is_draft = fields.Boolean(compute="_compute_state_flags")
    is_circulating = fields.Boolean(compute="_compute_state_flags")
    is_completed = fields.Boolean(compute="_compute_state_flags")
    is_returned = fields.Boolean(compute="_compute_state_flags")
    is_rejected = fields.Boolean(compute="_compute_state_flags")
    is_cancelled = fields.Boolean(compute="_compute_state_flags")
    is_terminal = fields.Boolean(compute="_compute_state_flags")
    is_editable = fields.Boolean(
        compute="_compute_state_flags",
        help="True while the หนังสือ may still be edited (draft or returned).",
    )

    # === Defaults ===
    @api.model
    def _default_sender_department_id(self):
        employee = self.env.user.employee_id
        return employee.department_id.id if employee and employee.department_id else False

    @api.model_create_multi
    def create(self, vals_list):
        """Every หนังสือ starts with the mandatory ผู้จัดทำ/ผู้ส่ง step (row 1) so it is
        always the first name in the Route (and locked from removal)."""
        docs = super().create(vals_list)
        for doc in docs:
            doc._ensure_originator_step()
        return docs

    # === Computes ===
    @api.depends("state")
    def _compute_state_flags(self):
        for record in self:
            record.is_draft = record.state == "draft"
            record.is_circulating = record.state == "circulating"
            record.is_completed = record.state == "completed"
            record.is_returned = record.state == "returned"
            record.is_rejected = record.state == "rejected"
            record.is_cancelled = record.state == "cancelled"
            record.is_terminal = record.state in ("rejected", "cancelled")
            record.is_editable = record.state in ("draft", "returned")

    @api.depends("origin_model", "origin_res_id")
    def _compute_origin_reference(self):
        for record in self:
            ref = False
            if record.origin_model and record.origin_res_id:
                model = self.env.get(record.origin_model)
                if model is not None:
                    origin = model.browse(record.origin_res_id)
                    if origin.exists():
                        ref = origin.display_name
            record.origin_reference = ref

    @api.depends(
        "routing_step_ids.state",
        "routing_step_ids.disposition",
        "routing_step_ids.verb",
        "routing_step_ids.is_originator",
    )
    def _compute_strongest_verb_done(self):
        for record in self:
            # Exclude the originator (ผู้จัดทำ) — their auto-signature at send is not
            # an approval, so it must not set has_signed (which would block the
            # sender's own ดึงกลับ / ยกเลิกการส่ง right after sending).
            done = record.routing_step_ids.filtered(
                lambda s: s.state == "done"
                and s.disposition in POSITIVE_DISPOSITIONS
                and not s.is_originator
            )
            strongest = done.mapped("verb").sorted(key=lambda v: v.rank)[-1:]
            record.strongest_verb_id = strongest
            record.has_signed = any(s.verb.is_signature for s in done)

    @api.depends("state", "has_signed", "sender_user_id")
    def _compute_can_withdraw(self):
        is_manager = self.env.user.has_group("agx_sarabun.group_sarabun_manager")
        for record in self:
            record.can_withdraw = (
                record.state == "circulating"
                and not record.has_signed
                and (record.sender_user_id == self.env.user or is_manager)
            )

    @api.depends(
        "routing_step_ids.state",
        "routing_step_ids.actor_user_ids",
        "routing_step_ids.recipient_ids.user_id",
    )
    def _compute_my_active_step(self):
        uid = self.env.user
        for record in self:
            # Act button: I'm a *current actor* on an active step (drops once I act
            # or delegate the step away).
            record.my_active_step_id = record.routing_step_ids.filtered(
                lambda s: s.state == "active" and uid in s.actor_user_ids
            )[:1]
            # "reaching" step drives the persistent incoming box + its columns. It is
            # keyed on my sarabun.step.recipient rows (the permanent per-person ledger,
            # never removed) — not the mutable actor_user_ids snapshot — so it survives
            # delegate / recall / reject. Active step preferred, else my latest.
            my_recips = record.routing_step_ids.recipient_ids.filtered(
                lambda r: r.user_id == uid
            )
            active = my_recips.filtered(lambda r: r.step_id.state == "active")[:1]
            # latest-reached: higher stage order, then later-created row (id monotonic)
            reaching = active or my_recips.sorted(
                key=lambda r: (r.step_id.order, r.id)
            )[-1:]
            record.my_reaching_step_id = reaching.step_id

    # Depend on the real routing_step_ids O2m (searchable), not the non-stored
    # my_reaching_step_id — Odoo can't resolve reverse triggers (e.g. when a verb
    # changes) through a non-stored computed M2o (UserWarning). my_reaching_step_id
    # is itself derived from these same routing_step_ids fields, so this is equivalent.
    @api.depends(
        "routing_step_ids.state",
        "routing_step_ids.verb",
        "routing_step_ids.recipient_ids.user_id",
        "routing_step_ids.recipient_ids.received_date",
        "routing_step_ids.recipient_ids.read_state",
    )
    def _compute_my_inbox(self):
        uid = self.env.user
        for record in self:
            step = record.my_reaching_step_id
            recipient = step.recipient_ids.filtered(lambda r: r.user_id == uid)[:1]
            # per-person "วันที่ได้รับ" — correct even when the step was delegated after
            # activation (the delegate received later than the step's activated_date).
            record.my_received_date = recipient.received_date
            record.my_action_verb_id = step.verb
            record.my_read_state = recipient.read_state or ("unread" if step else False)

    def action_mark_read(self):
        """Stamp read_date on the current user's recipient rows (called when they
        open the หนังสือ form). Opening IS reading — so every unread row of theirs on
        this หนังสือ is marked, not only the one on a still-active step (a รับทราบ / CC
        or already-acted recipient must flip to อ่านแล้ว too). Idempotent; only
        touches own rows. Waiting/future steps carry no recipient row yet, so nothing
        is marked before the หนังสือ actually reaches the user."""
        recipients = self.env["sarabun.step.recipient"].sudo().search([
            ("document_id", "in", self.ids),
            ("user_id", "=", self.env.user.id),
            ("read_date", "=", False),
        ])
        if recipients:
            recipients.write({"read_date": fields.Datetime.now()})
        return True

    @api.depends("routing_step_ids.state", "routing_step_ids.gating")
    def _compute_routing_progress(self):
        for record in self:
            steps = record.routing_step_ids
            record.pending_ack_count = len(
                steps.filtered(lambda s: s.state == "active" and not s.gating)
            )
            gating = steps.filtered("gating")
            if gating:
                done = gating.filtered(
                    lambda s: s.state == "done" and s.disposition in POSITIVE_DISPOSITIONS
                )
                record.routing_progress = 100.0 * len(done) / len(gating)
            else:
                record.routing_progress = 0.0

    @api.depends("signed_at")
    def _compute_is_frozen(self):
        for record in self:
            record.is_frozen = bool(record.signed_at)

    # === Display ===
    def name_get(self):
        result = []
        for record in self:
            name = record.name if record.name and record.name != "/" else _("New")
            if record.subject:
                name = f"{name} — {record.subject}"
            result.append((record.id, name))
        return result

    def _status_label(self):
        """Short human status for the origin record: state + routing progress +
        who the หนังสือ is waiting on right now. Consumed by
        sarabun.document.mixin.sarabun_state_label, so the source form can track the
        route — how far it has progressed AND who currently holds it — without
        opening the หนังสือ."""
        self.ensure_one()
        label = dict(self._fields["state"].selection).get(self.state, self.state)
        if self.state == "circulating":
            gating = self.routing_step_ids.filtered("gating")
            if gating:
                done = gating.filtered(
                    lambda s: s.state == "done"
                    and s.disposition in POSITIVE_DISPOSITIONS
                )
                label = _("%(state)s • ผ่านแล้ว %(done)s/%(total)s") % {
                    "state": label,
                    "done": len(done),
                    "total": len(gating),
                }
            # Who the หนังสือ awaits now — its active step(s). Prefer the gating
            # (blocking) ones; fall back to any active รับทราบ / CC step.
            active = self.routing_step_ids.filtered(lambda s: s.state == "active")
            active = active.filtered("gating") or active
            waiting = ", ".join(
                "%s: %s" % (s.verb.name, s.target_name) if s.target_name else s.verb.name
                for s in active
            )
            if waiting:
                label = _("%(label)s • กำลังรอ %(who)s") % {
                    "label": label, "who": waiting,
                }
        return label

    def action_view_origin(self):
        """Open the linked origin record (kept from the old API; harmless in P1)."""
        self.ensure_one()
        if not self.origin_model or not self.origin_res_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": self.origin_model,
            "res_id": self.origin_res_id,
            "view_mode": "form",
            "target": "current",
        }

    # ============================================================ #
    #  Lifecycle & routing engine (P2 — ADR-0001 / ADR-0002)        #
    #  Numbering (_register/_void_register) is P3; freeze is P5.     #
    # ============================================================ #

    # === Send / Recall (lifecycle transitions) ===
    def action_send(self):
        """draft|returned → circulating: ensure the ผู้จัดทำ step, seed the approver
        chain (if needed), auto-sign the originator (ส่ง = ลงนามผู้จัดทำ), register (P3),
        activate stage 1."""
        for doc in self:
            if doc.state not in ("draft", "returned"):
                raise UserError(_("Only draft or returned documents can be sent."))
            doc._ensure_originator_step()
            # Seed the approver chain only when it is still empty (the originator
            # step alone doesn't count).
            if doc.state == "draft" and not doc.routing_step_ids.filtered(
                lambda s: not s.is_originator
            ):
                doc._seed_route_from_template()
            if not doc.routing_step_ids.filtered("gating"):
                raise UserError(_(
                    "Add at least one gating step (เห็นชอบ or ลงนาม-อนุมัติ) before sending."
                ))
            doc._sign_originator_step()  # ส่ง = ลงนามของผู้จัดทำ (auto)
            doc._assign_register_number()  # P3: atomic per-(ส่วนงาน × type) allocation
            doc.state = "circulating"
            doc.message_post(body=_("Document sent for routing."))
            doc._call_origin("_on_sarabun_circulating", doc)
            doc._advance_stage()
        return True

    # === Originator (ผู้จัดทำ/ผู้ส่ง) — the mandatory, locked first step ===
    def _ensure_originator_step(self):
        """Guarantee the mandatory first step = the ผู้จัดทำ/ผู้ส่ง (is_originator),
        waiting until auto-signed at send. Idempotent — one active originator per
        attempt. Created at document create() and re-ensured after re-seed."""
        self.ensure_one()
        if self.routing_step_ids.filtered("is_originator"):
            return
        Step = self.env["sarabun.routing.step"]
        verb = self.env.ref("agx_sarabun.verb_originate", raise_if_not_found=False)
        orders = self.routing_step_ids.mapped("order")
        first_order = (min(orders) - 1) if orders else 1
        self.routing_step_ids = [(0, 0, {
            "order": first_order,
            "verb": (verb or Step._default_verb()).id,
            "is_originator": True,
            "target_mode": "person",
            "employee_id": self.sender_user_id.employee_id.id,
            "attempt_seq": self.attempt_seq or 1,
            "created_by_disposition": "seed",
            "state": "waiting",
        })]

    def _sign_originator_step(self):
        """Auto-sign the originator at send (ส่ง = ลงนามผู้จัดทำ). Idempotent; the
        write is sudo so it passes the originator write-guard."""
        self.ensure_one()
        step = self.routing_step_ids.filtered(
            lambda s: s.is_originator and s.state != "done"
        )[:1]
        if step:
            now = fields.Datetime.now()
            step.sudo().write({
                "state": "done",
                "disposition": "complete",
                "acted_by_id": self.sender_user_id.id,
                "acted_date": now,
                "sent_date": now,  # ส่ง = ลงนามผู้จัดทำ (auto at send)
            })

    def action_open_send_wizard(self):
        """Open the send confirmation wizard (the header Send button). The actual
        transition stays in action_send, which the wizard calls on confirm."""
        self.ensure_one()
        if self.state not in ("draft", "returned"):
            raise UserError(_("Only draft or returned documents can be sent."))
        return {
            "type": "ir.actions.act_window",
            "name": _("ยืนยันการส่งเอกสาร"),
            "res_model": "sarabun.send.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_document_id": self.id},
        }

    def _check_sender_withdraw_allowed(self):
        """Shared guard for the sender's ดึงกลับ / ยกเลิกการส่ง (ADR-0006): only
        while circulating, by the sender (or a manager), and before any
        ลงนาม-อนุมัติ step has occurred."""
        self.ensure_one()
        if self.state != "circulating":
            raise UserError(_("Only a circulating document can be withdrawn."))
        if self.sender_user_id != self.env.user and not self.env.user.has_group(
            "agx_sarabun.group_sarabun_manager"
        ):
            raise UserError(_("Only the sender may withdraw this document."))
        if self.has_signed:
            raise UserError(_(
                "This document has been signed; withdrawal now requires issuing a "
                "cancellation หนังสือ, not ดึงกลับ / ยกเลิกการส่ง."
            ))

    def action_pull_back(self, reason=None):
        """ดึงกลับ (recall) — circulating → returned, KEEPING the register number
        (ADR-0006). Archives the current chain and restarts on re-send: a
        self-initiated ตีกลับ-to-sender, so the หนังสือ becomes editable and can be
        revised and re-sent on the same number. Fires ``_on_sarabun_recalled``."""
        self.ensure_one()
        self._check_sender_withdraw_allowed()
        if not reason:
            raise UserError(_("A reason is required to ดึงกลับ (pull back)."))
        self.routing_step_ids._clear_activities()
        self._restart_chain()
        self.state = "returned"
        self.message_post(body=_("Document pulled back (ดึงกลับ). Reason: %s") % reason)
        self._call_origin("_on_sarabun_recalled", self)
        return True

    def action_recall(self, reason=None):
        """ยกเลิกการส่ง (cancel-send) — circulating → cancelled (terminal); the
        register number is VOIDED as a permanent gap (ADR-0006). Sender-only,
        before any ลงนาม-อนุมัติ step."""
        self.ensure_one()
        self._check_sender_withdraw_allowed()
        if not reason:
            raise UserError(_("A reason is required to ยกเลิกการส่ง (cancel the send)."))
        self.routing_step_ids._clear_activities()
        self.routing_step_ids.filtered(lambda s: s.state in ("waiting", "active")).write(
            {"state": "skipped"}
        )
        self.state = "cancelled"
        self._void_register("cancelled")
        self.message_post(body=_("Send cancelled (ยกเลิกการส่ง). Reason: %s") % reason)
        self._call_origin("_on_sarabun_cancelled", self)
        return True

    def action_open_recall_wizard(self):
        """Open the ดึงกลับ / ยกเลิกการส่ง wizard (collects the mandatory reason)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ดึงกลับ / ยกเลิกการส่ง"),
            "res_model": "sarabun.recall.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_document_id": self.id},
        }

    def action_act_on_my_step(self):
        """Open the act wizard for the current user's active step."""
        self.ensure_one()
        if not self.my_active_step_id:
            raise UserError(_("You have no pending action on this document."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Act on Step"),
            "res_model": "sarabun.step.act.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_step_id": self.my_active_step_id.id},
        }

    # === Inbox tray (P4 — systray) ===
    @api.model
    def get_my_sarabun_inbox(self, limit=20):
        """Documents awaiting the current user's action — powers the systray tray.

        The inbox is every หนังสือ with an *active* step whose snapshot holders
        include the current user (gating or รับทราบ alike). Returns the live total
        plus a capped, display-ready list. Runs as the user, so record rules apply.
        """
        steps = self.env["sarabun.routing.step"].search(
            [("state", "=", "active"), ("actor_user_ids", "in", self.env.user.id)]
        )
        docs = steps.mapped("document_id").filtered(lambda d: d.state == "circulating")
        documents = [
            {
                "id": d.id,
                "name": d.name,
                "subject": d.subject or "",
                "date": fields.Date.to_string(d.date) if d.date else "",
                "document_type": d.type_id.display_name or "",
            }
            for d in docs[:limit]
        ]
        return {"documents": documents, "total_count": len(docs)}

    def action_duplicate_to_draft(self):
        """rejected → a NEW draft linked to the same origin (1:N — ADR-0002 #8)."""
        self.ensure_one()
        new_doc = self.copy({"state": "draft", "name": "/", "attempt_seq": 1})
        return {
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document",
            "res_id": new_doc.id,
            "view_mode": "form",
            "target": "current",
        }

    # === Stage engine ===
    def _seed_route_from_template(self):
        """Materialise the seed template's lines into waiting steps (ADR-0001)."""
        self.ensure_one()
        template = self.route_template_id or self.type_id.default_route_id
        if not template:
            return
        self.route_template_id = template
        self.routing_step_ids = [
            (0, 0, dict(line._seed_vals(), attempt_seq=self.attempt_seq or 1))
            for line in template.line_ids
        ]

    def _shift_stages_from(self, order):
        """Make room for an inserted stage (เกษียนสั่งการ) at `order`."""
        self.ensure_one()
        for step in self.routing_step_ids.filtered(lambda s: s.order >= order):
            step.order = step.order + 1

    def _stage_complete(self, order):
        """A stage is passed when every gating step in it is positively done.
        A stage with no gating step never stalls the Route."""
        self.ensure_one()
        gating = self.routing_step_ids.filtered(lambda s: s.order == order and s.gating)
        if not gating:
            return True
        return all(
            s.state == "done" and s.disposition in POSITIVE_DISPOSITIONS for s in gating
        )

    def _advance_stage(self):
        """Activate stages in order; stop at the first stage with unfinished gating;
        complete the document when all gating is positively done."""
        self.ensure_one()
        if self.state != "circulating":
            return
        for order in sorted(set(self.routing_step_ids.mapped("order"))):
            waiting = self.routing_step_ids.filtered(
                lambda s: s.order == order and s.state == "waiting"
            )
            if waiting:
                waiting._activate()
            if not self._stage_complete(order):
                return  # frontier — wait for this stage's gating steps
        self._complete_document()

    def _complete_document(self):
        self.ensure_one()
        if self.state != "circulating":
            return
        self.state = "completed"
        self.routing_step_ids._clear_activities()  # clear any remaining to-dos
        self._freeze_signed_copy()  # P5
        self.message_post(body=_("All routing completed. Document is now complete."))
        self._call_origin("_on_sarabun_completed", self)

    # === Negative paths (driven from step dispositions) ===
    def _do_return(self, step, destination="sender_restart", resume_step_id=None):
        """ตีกลับ — send back for revision; destination chosen by the returner.

        Archive-not-overwrite (ADR-0006): the current attempt is ALWAYS frozen as
        history (``active=False``, ``attempt_seq`` bumped) — never reset in place.
        The new attempt re-seeds either the full template (restart) or just the
        chosen resume step onward (resume), leaving the prior chain intact."""
        self.ensure_one()
        self.routing_step_ids._clear_activities()  # drop to-dos before archive
        if destination == "resume_step" and resume_step_id:
            resume = self.env["sarabun.routing.step"].browse(int(resume_step_id))
            # Snapshot the tail's seed vals BEFORE archiving, then recreate them
            # fresh in the new attempt (the originals stay archived as history).
            tail = self.routing_step_ids.filtered(
                lambda s: s.order >= resume.order
            ).sorted("order")
            seeds = [s._resume_seed_vals() for s in tail]
            self._bump_attempt_and_archive()
            new_seq = self.attempt_seq or 1
            self.routing_step_ids = [
                (0, 0, dict(v, attempt_seq=new_seq)) for v in seeds
            ]
            self._ensure_originator_step()  # resume tail starts above row 1 — re-add it
        else:
            self._restart_chain()
        self.state = "returned"
        self.message_post(body=_("Document returned for revision (ตีกลับ)."))
        self._call_origin("_on_sarabun_returned", self, step)

    def _do_reject(self, step):
        """ปฏิเสธ — terminal; void the number, skip remaining steps."""
        self.ensure_one()
        self.routing_step_ids._clear_activities()
        self.routing_step_ids.filtered(lambda s: s.state in ("waiting", "active")).write(
            {"state": "skipped"}
        )
        self.state = "rejected"
        self._void_register("rejected")
        self.message_post(body=_("Document rejected (ปฏิเสธ)."))
        self._call_origin("_on_sarabun_rejected", self, step)

    def _bump_attempt_and_archive(self):
        """Freeze the current attempt's steps as history and start a new attempt."""
        self.ensure_one()
        self.routing_step_ids.write({"active": False})
        self.attempt_seq = (self.attempt_seq or 1) + 1

    def _restart_chain(self):
        """Archive the current chain and re-seed a fresh waiting one for a restart
        (ตีกลับ→sender_restart or ดึงกลับ). Prefer the route template; if the
        document has no template — the common from_record / ad-hoc case — recreate
        the just-archived chain's steps so the Route is never left empty (which
        would strand the หนังสือ in ``returned``, unable to re-send)."""
        self.ensure_one()
        seeds = [s._resume_seed_vals() for s in self.routing_step_ids.sorted("order")]
        self._bump_attempt_and_archive()
        self._seed_route_from_template()
        if not self.routing_step_ids:
            new_seq = self.attempt_seq or 1
            self.routing_step_ids = [
                (0, 0, dict(v, attempt_seq=new_seq)) for v in seeds
            ]
        # The archived attempt's originator is now inactive — re-add it (unless the
        # recreated seeds already carried one) so the new attempt keeps its row 1.
        self._ensure_originator_step()

    # === Origin adapter dispatch (ADR-0004: same txn, no swallow) ===
    def _call_origin(self, method, *args):
        """Dispatch an origin callback in the actor's transaction (ADR-0004 §8.7).
        sudo() is used because the approver legitimately lacks rights on the origin,
        but there is NO try/except — a raising callback propagates and rolls the
        whole action back (correctness over availability; no silent swallow)."""
        self.ensure_one()
        if not (self.origin_model and self.origin_res_id):
            return
        model = self.env.get(self.origin_model)
        if model is None:
            return
        origin = model.sudo().browse(self.origin_res_id)
        if not origin.exists():
            return
        fn = getattr(origin, method, None)
        if fn:
            fn(*args)

    # === Numbering / Register (P3 — ADR-0002 §4) ===
    @api.constrains("numbering_mode", "kind")
    def _check_numbering_mode_scope(self):
        for doc in self:
            if doc.kind == "from_record" and doc.numbering_mode != "auto":
                raise ValidationError(_(
                    "from_record documents register automatically; "
                    "reserved/gap/manual numbering is for manual compose only."
                ))

    def _resolve_sequence(self):
        """Resolve the register from the sender ส่วนงาน — one shared register per
        unit across all document types. Block on missing; never number from a
        default pool (DESIGN §4.2)."""
        self.ensure_one()
        seq = self.env["sarabun.document.sequence"].search([
            ("sender_department_id", "=", self.sender_department_id.id),
            ("active", "=", True),
        ], limit=1)
        if not seq:
            raise UserError(_(
                "ไม่พบทะเบียนหนังสือสำหรับส่วนงาน '%(unit)s'. "
                "(No register configured for unit '%(unit)s'.) "
                "Configure a register before sending."
            ) % {"unit": self.sender_department_id.display_name})
        return seq

    def _assign_register_number(self):
        """ลงทะเบียน — the distinct Register seam (phase-2 clerk gate lands here).
        Idempotent: a returned document keeps its number on re-send.

        NOTE: do not rename back to ``_register`` — that name is reserved by
        Odoo's ORM (BaseModel._register, the registry-visibility flag) and gets
        clobbered to a bool on registry reload."""
        self.ensure_one()
        if self.register_number_id:
            return
        seq = self._resolve_sequence()
        if self.numbering_mode == "reserved":
            number = self.reserved_number_id
            if not number or number.state != "reserved" or number.sequence_id != seq:
                raise UserError(_("Select a valid reserved number for this register."))
            number.write({
                "state": "used",
                "document_id": self.id,
                "used_date": fields.Datetime.now(),
            })
        elif self.numbering_mode in ("manual", "gap"):
            if not self.manual_counter:
                raise UserError(_("Enter the number to use."))
            number = seq.allocate(self, counter=self.manual_counter)
        else:  # auto
            number = seq.allocate(self)
        self.register_number_id = number
        self.name = number.register_number

    def _void_register(self, reason):
        """Void the register number as a permanent gap (เลขยกเลิก) — never reissued."""
        self.ensure_one()
        if self.register_number_id:
            self.register_number_id.write({
                "state": "voided",
                "void_reason": reason,
                "void_date": fields.Datetime.now(),
            })

    # === Signing / official record (P5 — DESIGN §5) ===
    def _signature_steps(self):
        """Completed ลงนาม-อนุมัติ steps — the signature block(s)."""
        self.ensure_one()
        return self.routing_step_ids.filtered(
            lambda s: s.state == "done"
            and s.disposition in POSITIVE_DISPOSITIONS
            and s.verb.is_signature
        ).sorted(key=lambda s: (s.order, s.acted_date or s.id))

    def _kasian_trail_steps(self):
        """The เกษียน/endorsement trail — AUDIT ONLY (ADR-0008). No longer rendered on
        the official document (the document shows signatures only — see
        _signature_block_steps); kept for UI / audit uses."""
        self.ensure_one()
        return self.routing_step_ids.filtered(
            lambda s: s.state == "done"
            and s.disposition in POSITIVE_DISPOSITIONS
            and s.verb.gating
        ).sorted(key=lambda s: (s.order, s.acted_date or s.id))

    def _signature_block_steps(self):
        """Signatures rendered on the official document (ADR-0008): every positive-done
        step whose verb has show_signature — the signing ผู้จัดทำ + เห็นชอบ +
        ลงนาม-อนุมัติ — in one uniform ลงนาม/อนุมัติ format, ordered by stage. Non-signing
        verbs (ตรวจสอบ / พิจารณา / ส่งต่อ, a non-signing ผู้จัดทำ) render nothing; the
        routing trail is audit-only."""
        self.ensure_one()
        return self.routing_step_ids.filtered(
            lambda s: s.state == "done"
            and s.disposition in POSITIVE_DISPOSITIONS
            and s.verb.show_signature
        ).sorted(key=lambda s: (s.order, s.acted_date or s.id))

    def _get_delegated_report_action(self):
        """The origin's report — the official PDF body for a has-source Document
        (delegation contract, ADR-0004). The source report embeds the endorsement
        block at its own tail (ADR-0007); False → this Document has no source report
        and renders our own standalone report instead."""
        self.ensure_one()
        if self.origin_model and self.origin_res_id:
            model = self.env.get(self.origin_model)
            if model is not None:
                origin = model.browse(self.origin_res_id)
                if origin.exists() and hasattr(origin, "_get_sarabun_report_action"):
                    return origin._get_sarabun_report_action()
        return False

    def _get_report_base_filename(self):
        self.ensure_one()
        name = (self.name or "").replace("/", "-") or "sarabun"
        return f"{name} - {self.subject or ''}".strip()

    def _render_official_pdf(self):
        """The official PDF — a SINGLE report, no cover sheet, no merge (ADR-0007).
        Rendered with sudo — the frozen copy is the system's official record.

        has-source: the origin's delegated report, which `t-call`s the endorsement
        block (เกษียน trail + signature) at its own tail. no-source: our own
        standalone document report (header + เนื้อหา + the same block)."""
        self.ensure_one()
        Report = self.env["ir.actions.report"].sudo()
        delegated = self._get_delegated_report_action()
        if delegated and self.origin_res_id:
            pdf, _dummy = Report._render_qweb_pdf(
                delegated.report_name, [self.origin_res_id]
            )
        else:
            pdf, _dummy = Report._render_qweb_pdf(
                "agx_sarabun.action_report_sarabun_document", [self.id]
            )
        return pdf

    def _get_official_pdf(self):
        """Frozen bytes once completed; a live render before that (§5.4)."""
        self.ensure_one()
        if self.is_frozen and self.signed_pdf:
            return base64.b64decode(self.signed_pdf)
        return self._render_official_pdf()

    def _render_preview_html(self):
        """On-screen HTML preview — the SAME report as the PDF, rendered as HTML (fast,
        no wkhtmltopdf) and framed to A4 (ADR-0007). This is a screen preview only; the
        official record stays the PDF (freeze / print). Always a live render."""
        self.ensure_one()
        Report = self.env["ir.actions.report"].sudo()
        delegated = self._get_delegated_report_action()
        if delegated and self.origin_res_id:
            html, _dummy = Report._render_qweb_html(
                delegated.report_name, [self.origin_res_id]
            )
        else:
            html, _dummy = Report._render_qweb_html(
                "agx_sarabun.action_report_sarabun_document", [self.id]
            )
        return self._frame_preview_html(html)

    def _frame_preview_html(self, html):
        """Constrain the report's .page to A4 on a page-like backdrop so the HTML
        preview reads like the printed sheet. Injected last, so it wins over the
        report's own .page rules."""
        if isinstance(html, bytes):
            html = html.decode("utf-8")
        style = (
            "<style>"
            "body{background:#d9d9d9 !important;margin:0;}"
            ".page{position:relative;box-sizing:border-box;width:210mm;"
            "min-height:296mm;margin:12px auto;padding:15mm;background:#fff;"
            "box-shadow:0 1px 6px rgba(0,0,0,.35);}"
            "</style>"
        )
        if "</body>" in html:
            html = html.replace("</body>", style + "</body>", 1)
        else:
            html += style
        return html.encode("utf-8")

    def _freeze_signed_copy(self):
        """Freeze the immutable ฉบับลงนาม at completion (idempotent, one-way)."""
        self.ensure_one()
        if self.is_frozen:
            return
        pdf = self._render_official_pdf()
        self.write({
            "signed_pdf": base64.b64encode(pdf),
            "signed_pdf_filename": self._get_report_base_filename() + ".pdf",
            "signed_at": fields.Datetime.now(),
        })

    def action_print_report(self):
        """Open the official PDF (frozen if completed, else a live preview)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/sarabun/document/%s/pdf" % self.id,
            "target": "new",
        }

    def action_open_pdf_preview(self):
        """Open the official PDF in a preview dialog (ADR-0007) — the draft
        'ดูตัวอย่างเอกสาร' button, since a draft has no inline preview yet. Sent
        documents preview inline in the form via the sarabun_pdf_inline widget."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "sarabun_pdf_preview",
            "name": _("ตัวอย่างเอกสาร (Preview)"),
            "target": "new",
            "params": {"doc_id": self.id, "doc_name": self.display_name},
        }
