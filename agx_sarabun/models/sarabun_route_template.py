# -*- coding: utf-8 -*-
"""Route templates — seed-only (ADR-0001).

A template *seeds* a Document's Route at send time; it never owns or constrains
the flow once seeded. Each template line materialises into one
``sarabun.routing.step`` (state ``waiting``).
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

# Keep in sync with sarabun_routing_step.py
TARGET_MODE = [
    ("unit", "ธุรการหน่วยงาน (Unit Clerk)"),
    ("person", "บุคลากร (Personnel)"),
    ("position", "ตำแหน่ง (Position)"),
]


class SarabunRouteTemplate(models.Model):
    _name = "sarabun.route.template"
    _description = "Sarabun Route Template (seed)"
    _order = "sequence, name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10, help="Match priority (lower = higher).")
    description = fields.Text()

    # Scope (for from_record auto-matching)
    department_id = fields.Many2one("hr.department", string="Department")
    document_type_id = fields.Many2one("sarabun.document.type", string="Document Type")
    type_origin_model_id = fields.Many2one(
        related="document_type_id.origin_model_id",
        string="Type Origin Model",
        help="ไม่ store — ใช้ขับ attrs และอ่านใน constrains เท่านั้น "
        "(ระบบงานต้นทางที่ประเภทเอกสารบังคับไว้ ถ้ามี).",
    )
    # origin_model (the technical name) stays the source of truth — the bridge seed
    # data (purchase_request_sarabun, disbursement_sarabun, …) sets it as a Char and
    # find_matching_templates keys off it — while origin_model_id is a convenience
    # ir.model picker layered over it (compute reads it, inverse writes it back).
    origin_model_id = fields.Many2one(
        "ir.model",
        string="Origin Model",
        compute="_compute_origin_model_id",
        inverse="_inverse_origin_model_id",
        help="แหล่งที่มา — the source record's model this template auto-matches "
        "(e.g. purchase.request). Empty = match any source model.",
    )
    origin_model = fields.Char(string="Origin Model (technical)")
    condition_domain = fields.Char(
        string="Condition Domain",
        help="Python domain evaluated against the origin record, e.g. "
        "[('amount_total', '>=', 100000)]. Empty = match all.",
    )

    @api.depends("origin_model")
    def _compute_origin_model_id(self):
        IrModel = self.env["ir.model"]
        for template in self:
            template.origin_model_id = (
                IrModel._get(template.origin_model) if template.origin_model else False
            )

    def _inverse_origin_model_id(self):
        for template in self:
            template.origin_model = template.origin_model_id.model or False

    @api.onchange("origin_model_id")
    def _onchange_origin_model_id(self):
        # Keep the technical name live so the condition_domain widget (which reads
        # origin_model) re-targets the moment a model is picked, before save.
        self.origin_model = self.origin_model_id.model or False

    @api.onchange("document_type_id")
    def _onchange_document_type_id(self):
        # A type that declares its origin model wins over whatever the template had —
        # set both fields directly rather than relying on chaining from
        # _onchange_origin_model_id above. A type with no declared model leaves the
        # template's own choice untouched (still model-agnostic).
        type_model = self.document_type_id.origin_model_id
        if type_model:
            self.origin_model_id = type_model
            self.origin_model = type_model.model

    line_ids = fields.One2many(
        "sarabun.route.template.line", "template_id", string="Steps", copy=True
    )
    next_line_order = fields.Integer(
        compute="_compute_next_line_order",
        help="Default ลำดับ for the next seed line — max(existing) + 1 so new lines "
        "auto-increment instead of always starting at 1 (fed to line_ids' context).",
    )

    @api.depends("line_ids.order")
    def _compute_next_line_order(self):
        for record in self:
            orders = record.line_ids.mapped("order")
            record.next_line_order = (max(orders) + 1) if orders else 1

    @api.constrains("document_type_id", "origin_model")
    def _check_document_type_origin_model(self):
        for template in self:
            type_model = template.document_type_id.origin_model_id
            if type_model and template.origin_model and template.origin_model != type_model.model:
                raise ValidationError(_(
                    'แม่แบบเส้นทาง "%(template)s" ผูกประเภทเอกสาร "%(doc_type)s" ซึ่งบังคับระบบงานต้นทางเป็น '
                    '"%(model)s" — Origin Model ของแม่แบบต้องตรงกัน.'
                ) % {
                    "template": template.name,
                    "doc_type": template.document_type_id.name,
                    "model": type_model.model,
                })

    def match_origin_record(self, origin_record):
        self.ensure_one()
        if not self.condition_domain:
            return True
        try:
            domain = safe_eval(self.condition_domain, {"uid": self.env.uid})
            return bool(origin_record.filtered_domain(domain))
        except Exception:
            return False

    @api.model
    def find_matching_templates(self, origin_record=False, department_id=False, document_type_id=False):
        domain = [("active", "=", True)]
        if origin_record:
            domain += ["|", ("origin_model", "=", False), ("origin_model", "=", origin_record._name)]
        if department_id:
            domain += ["|", ("department_id", "=", False), ("department_id", "=", department_id)]
        if document_type_id:
            domain += ["|", ("document_type_id", "=", False), ("document_type_id", "=", document_type_id)]
        templates = self.search(domain, order="sequence, name")
        if origin_record:
            templates = templates.filtered(lambda t: t.match_origin_record(origin_record))
        return templates


class SarabunRouteTemplateLine(models.Model):
    _name = "sarabun.route.template.line"
    _description = "Sarabun Route Template Line (seed)"
    _order = "order, id"

    template_id = fields.Many2one(
        "sarabun.route.template", required=True, ondelete="cascade"
    )
    order = fields.Integer(string="Stage", default=1, help="Steps sharing one order run in parallel.")
    verb = fields.Many2one(
        "sarabun.verb",
        string="Verb",
        required=True,
        default=lambda self: self.env.ref("agx_sarabun.verb_endorse", raise_if_not_found=False),
        ondelete="restrict",
    )
    for_info = fields.Boolean(string="สำเนาเรียน (CC)", help="Non-gating acknowledge (CC).")
    target_mode = fields.Selection(TARGET_MODE, required=True, default="position")
    position_id = fields.Many2one("sarabun.position", string="Position")
    employee_id = fields.Many2one("hr.employee", string="บุคลากร (Person)")
    department_id = fields.Many2one(
        "hr.department", string="Unit",
        domain=[("is_sarabun_office", "=", True)],
        help="เป้าหมายแบบ ธุรการหน่วยงาน — เลือกได้เฉพาะหน่วยงานที่ตั้งเป็นหน่วยงานธุรการ.",
    )

    def _seed_vals(self):
        """Return the dict to create a sarabun.routing.step (state waiting)."""
        self.ensure_one()
        return {
            "order": self.order,
            "verb": self.verb.id,
            "for_info": self.for_info,
            "target_mode": self.target_mode,
            "position_id": self.position_id.id,
            "employee_id": self.employee_id.id,
            "department_id": self.department_id.id,
            "state": "waiting",
            "created_by_disposition": "seed",
            "seeded_from_template_line_id": self.id,
        }
