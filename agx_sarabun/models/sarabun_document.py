# -*- coding: utf-8 -*-
"""sarabun.document — the หนังสือ (Document), protagonist of e-Saraban.

P1 scope: the static data foundation only (header, classification, origin link,
อ้างถึง / สิ่งที่ส่งมาด้วย, lifecycle state field). The routing engine and the
lifecycle state *machine* (transitions, _register, freeze, callbacks) arrive in
P2–P5 — see DESIGN.md and IMPLEMENTATION-PLAN.md. Methods here are intentionally
minimal; behaviour is added per phase.
"""
import logging

from odoo import _, api, fields, models

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

    # === Header (เรื่อง / เรียน / ผ่าน / วันที่) ===
    subject = fields.Char(string="เรื่อง (Subject)", required=True, tracking=True)
    date = fields.Date(
        string="วันที่ (Document Date)",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    addressee = fields.Char(
        string="เรียน (Addressee)",
        tracking=True,
        help="The ceremonial recipient on the หนังสือ header — its own field, "
        "separate from the routing actors. Manual or origin-set.",
    )
    addressee_position_id = fields.Many2one(
        comodel_name="sarabun.position",
        string="Addressee Position",
        help="Optional structured suggest source for เรียน (e.g. the final "
        "ลงนาม-อนุมัติ step's Position).",
    )
    through = fields.Char(
        string="ผ่าน (Through)",
        help='Free text for "เรียน X ผ่าน Y".',
    )

    # === Sender (ส่วนงานเจ้าของเรื่อง) ===
    sender_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Sender",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        tracking=True,
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

    # === Levels ===
    urgency = fields.Selection(
        selection=[
            ("normal", "ปกติ (Normal)"),
            ("urgent", "ด่วน (Urgent)"),
            ("very_urgent", "ด่วนมาก (Very Urgent)"),
            ("immediate", "ด่วนที่สุด (Immediate)"),
        ],
        string="ชั้นความเร็ว (Urgency)",
        default="normal",
        tracking=True,
    )
    secrecy = fields.Selection(
        selection=[
            ("normal", "ปกติ (Normal)"),
            ("confidential", "ลับ (Confidential)"),
            ("secret", "ลับมาก (Secret)"),
            ("top_secret", "ลับที่สุด (Top Secret)"),
        ],
        string="ชั้นความลับ (Secrecy)",
        default="normal",
        tracking=True,
        help="v1: display label only. Need-to-know enforcement is phase-2.",
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

    # === Computes ===
    @api.depends("state")
    def _compute_state_flags(self):
        for record in self:
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

    # === Display ===
    def name_get(self):
        result = []
        for record in self:
            name = record.name if record.name and record.name != "/" else _("New")
            if record.subject:
                name = f"{name} — {record.subject}"
            result.append((record.id, name))
        return result

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

    # === Workflow (P2 — ADR-0001/0002) ===
    # action_send(), action_recall(), _register(), _advance_stage(),
    # _freeze_signed_copy(), the routing.step engine and the lifecycle state
    # machine are implemented in later phases. They are intentionally absent in
    # P1 so the data foundation can be reviewed and installed on its own.
