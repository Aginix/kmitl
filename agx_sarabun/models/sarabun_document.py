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
    # An involved holder is read-only on the หนังสือ (see security.xml), yet the
    # awaiting-action surface is now native mail.activity (ADR-0014), whose
    # read/search/read_group delegate to this document's _mail_post_access
    # (mail.thread default 'write'). Set it to 'read' so a read-only holder can
    # read / count / open their own Todo without AccessError (ADR-0013). Accepted
    # side effect: a document-reader may also post chatter on the หนังสือ.
    _mail_post_access = "read"

    # === Identification ===
    name = fields.Char(
        string="Document Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
        index="trigram",
        help="Official registered number (running number only — no ปีงบ in the number; "
        "the year lives on ลงวันที่). Assigned only when the final approver signs — "
        "completion (ADR-0010); stays '/' while draft/circulating.",
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
        help="ลงวันที่ — the หนังสือ's official date, printed beside ที่. It is the "
        "date it is ส่ง (issued into circulation), (re)stamped at action_send "
        "(ADR-0010), NOT the create-draft date — so a draft held over ปีงบประมาณ "
        "year-end is dated in the new year when actually sent. Owner-editable is a "
        "later phase; kept read-only in the form for now.",
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
    include_content = fields.Boolean(
        string="แนบเนื้อหา (บันทึกนำ)",
        compute="_compute_include_content",
        store=True,
        readonly=False,
        help="Whether the เนื้อหา body is written on this หนังสือ. A composed "
        "(no-source) document always has it; a from_record document defaults to "
        "OFF (its origin report is the body) but may opt in to add a covering note "
        "above the origin's report.",
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
            ("returned", "รอการแก้ไขเอกสาร (Pending Revision)"),
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

    # === สิ่งที่ส่งมาด้วย (Enclosures) — plain attached files (feedback) ===
    enclosure_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="sarabun_document_enclosure_rel",
        column1="document_id",
        column2="attachment_id",
        string="สิ่งที่ส่งมาด้วย (Enclosures)",
        help="Files enclosed with the หนังสือ, managed through the attachments widget "
        "(just the files — no caption or ordering). Listed by filename under "
        "สิ่งที่ส่งมาด้วย on the printed document.",
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
        # Audit accessor only — the form no longer lists prior attempts beside the
        # live Route (a ดึงกลับ / ตีกลับ / รีเซ็ต re-runs the whole เส้นทาง).
        # Without active_test=False the ORM drops every archived row on the way out
        # (_RelationalMulti.convert_to_record filters x2many values by `active`
        # whenever active_test is on): the domain fetches them and the record
        # conversion then hands back an empty set, so every reader saw nothing.
        context={"active_test": False},
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
    reached_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="sarabun_document_reached_user_rel",
        column1="document_id",
        column2="user_id",
        string="Reached Users",
        compute="_compute_reached_user_ids",
        store=True,
        help="Everyone the หนังสือ has ever reached — the union of "
        "sarabun.step.recipient holders across ACTIVE and ARCHIVED steps. The "
        "read-visibility key (ADR-0013): being involved is a property of the "
        "หนังสือ, not of the current attempt, so read persists after completion and "
        "across ตีกลับ / ดึงกลับ / Reset. It only grows — a recipient row is never "
        "removed — matching the permanent per-person reach ledger of the Incoming box.",
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
    next_step_order = fields.Integer(
        compute="_compute_next_step_order",
        help="Default ลำดับ (Stage) for the next routing step added on the form — "
        "max(existing) + 1 so new steps auto-increment instead of always starting at "
        "1. Fed to routing_step_ids' context as default_order.",
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
    sequence_id = fields.Many2one(
        comodel_name="sarabun.document.sequence",
        string="เล่มทะเบียน (Register Book)",
        compute="_compute_sequence_id",
        store=True,
        readonly=False,
        copy=False,
        domain="[('sender_department_id', '=', sender_department_id), ('active', '=', True)]",
        help="เล่มทะเบียนที่จะใช้ออกเลขหนังสือฉบับนี้ (ADR-0012) — ตั้งต้นจากเล่มทะเบียนหลัก "
        "ของหน่วยงาน เปลี่ยนได้ก่อนส่ง และถูกตรึงไว้ตอนส่ง.",
    )
    register_number_id = fields.Many2one(
        comodel_name="sarabun.document.number",
        string="Register Number",
        readonly=True,
        copy=False,
        help="The register ledger row assigned by ลงทะเบียน at completion (ADR-0010).",
    )
    numbering_mode = fields.Selection(
        selection=[
            ("auto", "Auto (next available)"),
            ("reserved", "Reserved number"),
        ],
        string="Numbering Mode",
        default="auto",
        help="from_record always registers automatically; reserved (a pre-reserved "
        "number) is for manual compose (memo/circular).",
    )
    reserved_number_id = fields.Many2one(
        comodel_name="sarabun.document.number",
        string="Reserved Number",
        domain="[('state', '=', 'reserved'), ('sequence_id', '=', sequence_id)]",
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

    @api.depends("origin_model")
    def _compute_include_content(self):
        """A no-source (composed) หนังสือ always carries its own body; a from_record
        one defaults OFF (the origin report is the body). Editable — the drafter may
        opt a from_record document in to add a covering note."""
        for record in self:
            record.include_content = not record.origin_model

    @api.depends("sender_department_id")
    def _compute_sequence_id(self):
        """Default the เล่มทะเบียน from the unit (its เล่มทะเบียนหลัก, or its only book)
        — so the drafter never has to pick when the unit keeps a single register.
        Editable (readonly=False) until sent; a numbered หนังสือ keeps the book its
        number actually came from."""
        for record in self:
            if record.register_number_id:
                record.sequence_id = record.register_number_id.sequence_id
            elif record.sender_department_id:
                record.sequence_id = record.sender_department_id._sarabun_default_sequence()
            else:
                record.sequence_id = False

    @api.constrains("sequence_id", "sender_department_id")
    def _check_sequence_department(self):
        for record in self:
            seq = record.sequence_id
            if seq and seq.sender_department_id != record.sender_department_id:
                raise ValidationError(_(
                    "เล่มทะเบียน '%(book)s' ไม่ใช่ของหน่วยงาน '%(unit)s'."
                ) % {
                    "book": seq.display_name,
                    "unit": record.sender_department_id.display_name,
                })

    @api.depends("origin_model", "origin_res_id")
    def _compute_origin_reference(self):
        for record in self:
            ref = False
            if record.origin_model and record.origin_res_id:
                model = self.env.get(record.origin_model)
                if model is not None:
                    # sudo: whoever may read the หนังสือ (Route visibility) sees the
                    # origin's name as a reference on it, even without rights on the
                    # origin record itself — the หนังสือ's ACL governs, not the origin's.
                    origin = model.sudo().browse(record.origin_res_id)
                    if origin.exists():
                        ref = origin.display_name
            record.origin_reference = ref

    @api.depends(
        "routing_step_ids.recipient_ids.user_id",
        "archived_step_ids.recipient_ids.user_id",
    )
    def _compute_reached_user_ids(self):
        """Aggregate every recipient holder across ACTIVE and ARCHIVED steps
        (ADR-0013). Recipient rows carry a stored ``document_id``, so a direct
        search — under ``sudo`` and ``active_test=False`` — spans archived attempts
        that the ``active``-scoped ``routing_step_ids`` traversal would drop. The
        field only ever grows (rows are never deleted), so read never lapses."""
        Recipient = (
            self.env["sarabun.step.recipient"]
            .sudo()
            .with_context(active_test=False)
        )
        for record in self:
            rid = record.id if isinstance(record.id, int) else record._origin.id
            recips = (
                Recipient.search([("document_id", "=", rid)])
                if rid
                else Recipient.browse()
            )
            record.reached_user_ids = [(6, 0, recips.user_id.ids)]

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

    @api.depends("routing_step_ids.order")
    def _compute_next_step_order(self):
        """The Stage a freshly-added step should default to: one past the highest
        existing order (the originator sits at row 1), so the ลำดับ auto-increments
        instead of every new step landing on 1."""
        for record in self:
            orders = record.routing_step_ids.mapped("order")
            record.next_step_order = (max(orders) + 1) if orders else 1

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
        # While unnumbered (draft → circulating → returned, until completion —
        # ADR-0010) the หนังสือ is identified purely by its เรื่อง; no interim
        # code. The official number prefixes the เรื่อง only once ลงทะเบียน runs
        # at completion.
        result = []
        for record in self:
            numbered = record.name and record.name != "/"
            if numbered:
                label = (
                    f"{record.name} — {record.subject}"
                    if record.subject
                    else record.name
                )
            else:
                label = record.subject or _("(ยังไม่มีเรื่อง)")
            result.append((record.id, label))
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
        chain (if needed), auto-sign the originator (ส่ง = ลงนามผู้จัดทำ), activate
        stage 1. The official number is NOT assigned here — ลงทะเบียน now runs only
        when the final approver signs (see ``_complete_document``); send merely
        verifies a register resolves so the route can't strand at completion."""
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
            # P3: fail fast if no register resolves, and PIN the resolved เล่มทะเบียน
            # so a later config change can't move the หนังสือ to another book between
            # ส่ง and ลงทะเบียน (which runs at completion — ADR-0010/0011).
            doc.sequence_id = doc._resolve_sequence()
            doc._sign_originator_step()  # ส่ง = ลงนามของผู้จัดทำ (auto)
            # ลงวันที่ = the ส่ง (issue) date, not the create-draft date (ADR-0010): a
            # draft held over from the old ปีงบประมาณ is dated when it is actually sent
            # in the new one, so ที่ and ลงวันที่ stay in the same fiscal year (a หนังสือ
            # never straddles the year boundary). Re-stamped on each re-send.
            doc.date = fields.Date.context_today(doc)
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
            step = step.sudo()  # passes the originator write-guard
            vals = {
                "state": "done",
                "disposition": "complete",
                "acted_by_id": self.sender_user_id.id,
                "acted_date": now,
                "sent_date": now,  # ส่ง = ลงนามผู้จัดทำ (auto at send)
            }
            # Freeze the drafter's signature identity when the originator verb signs
            # (ลงนามผู้จัดทำ); a non-signing จัดทำ/ร่าง verb snapshots nothing (ADR-0009).
            if step.verb.show_signature:
                vals.update(step._signature_snapshot_vals(self.sender_user_id))
            step.write(vals)

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

    # The awaiting-action surface is native mail.activity now (ADR-0014): the
    # bespoke systray + its get_my_sarabun_inbox RPC and sarabun_inbox bus were
    # dissolved. The persistent กล่องหนังสือเข้า (Incoming box) menu/action stays.

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
        # ลงทะเบียน happens HERE — the number runs only once the final ลงนาม/อนุมัติ is
        # in (ADR-0010). Must precede the freeze so the frozen PDF carries the number.
        self._assign_register_number()
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
        """Freeze the current attempt's steps as history and start a new attempt.

        sudo: archiving is an ENGINE write over the whole chain — the originator row
        included — so it must pass the ผู้จัดทำ/ผู้ส่ง write-guard. Without it the
        sender's own ดึงกลับ (which runs in their user env, unlike a returner's
        sudoed ตีกลับ) died on "the ผู้จัดทำ/ผู้ส่ง step is fixed"."""
        self.ensure_one()
        self.routing_step_ids.sudo().write({"active": False})
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
                    "reserved numbering is for manual compose only."
                ))

    def _resolve_sequence(self):
        """Resolve the เล่มทะเบียน this หนังสือ issues from (ADR-0012): the book chosen
        on the document, else the unit's เล่มทะเบียนหลัก / only book. Block on missing
        or ambiguous; never number from a default pool (DESIGN §4.2)."""
        self.ensure_one()
        dept = self.sender_department_id
        # An archived book must not issue a number: sequence_id is a stored compute
        # snapshotted at create, so a draft can still hold a book the unit retired
        # afterwards. Treat an inactive pick as unset and fall back to the unit's
        # (active) default — everywhere else already filters archived books out.
        seq = (self.sequence_id.active and self.sequence_id) or (
            dept and dept._sarabun_default_sequence()
        )
        if not seq:
            unit = dept.display_name
            if dept and dept._sarabun_registers():
                raise UserError(_(
                    "ส่วนงาน '%(unit)s' มีหลายเล่มทะเบียน — โปรดเลือกเล่มทะเบียนที่จะใช้ส่ง "
                    "(หรือกำหนดเล่มทะเบียนหลักของหน่วยงาน)."
                ) % {"unit": unit})
            raise UserError(_(
                "ไม่พบทะเบียนหนังสือสำหรับส่วนงาน '%(unit)s'. "
                "(No register configured for unit '%(unit)s'.) "
                "Configure a register before sending."
            ) % {"unit": unit})
        return seq

    def _assign_register_number(self):
        """ลงทะเบียน — the distinct Register seam (phase-2 clerk gate lands here).
        Called at completion (ADR-0010): the number runs only once the final
        ลงนาม/อนุมัติ is in, so a document that is rejected/cancelled mid-route never
        consumes a number. Idempotent (guarded on ``register_number_id``).

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
        else:  # auto
            number = seq.allocate(self)
        self.register_number_id = number
        self.name = number.register_number

    def _void_register(self, reason):
        """Void the register number as a permanent gap (เลขยกเลิก) — never reissued.

        Since ADR-0010 the number is assigned at completion, so reject/cancel (both
        pre-completion) find no number to void — this is a guarded no-op on the normal
        path, kept for the ledger's reserved/manual paths and belt-and-braces."""
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
        and renders our own standalone report instead.

        Resolved under sudo: rendering the official document is a SYSTEM operation
        gated by the หนังสือ's own read access (the controller checks it), so a Route
        recipient without rights on the origin still gets the correct report — and an
        origin override that reads its own fields here never trips the recipient's ACL."""
        self.ensure_one()
        if self.origin_model and self.origin_res_id:
            model = self.env.get(self.origin_model)
            if model is not None:
                origin = model.sudo().browse(self.origin_res_id)
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
        """Freeze the immutable ฉบับลงนาม at completion (idempotent, one-way) AND drop
        a visible copy into the หนังสือ's Attachments (feedback).

        ``signed_pdf`` is a ``res_field``-backed Binary — Odoo hides such attachments
        from the record's attachment list — so on its own the approved PDF never
        surfaces in the chatter box. A second plain ``ir.attachment`` (``res_field``
        unset) is what actually appears in the record's data for download."""
        self.ensure_one()
        if self.is_frozen:
            return
        pdf = self._render_official_pdf()
        filename = self._get_report_base_filename() + ".pdf"
        datas = base64.b64encode(pdf)
        self.write({
            "signed_pdf": datas,
            "signed_pdf_filename": filename,
            "signed_at": fields.Datetime.now(),
        })
        # sudo: completion runs in the final approver's env and the freeze is a system
        # act — they may lack ir.attachment create rights for this record.
        self.env["ir.attachment"].sudo().create({
            "name": filename,
            "datas": datas,
            "res_model": "sarabun.document",
            "res_id": self.id,
            "mimetype": "application/pdf",
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
