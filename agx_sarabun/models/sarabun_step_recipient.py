# -*- coding: utf-8 -*-
"""sarabun.step.recipient — per-person route + read tracking.

One row per (routing step × resolved holder). Even a ธุรการหน่วยงาน / ตำแหน่ง with
several holders keeps a separate row per person, so read status is tracked
individually. Materialised when a step activates (snapshot); ``read_date`` is
stamped when that user first opens the document (P4). ``forwarded`` (รอการส่งต่อ)
is a phase-2 seam, unused in v1.
"""
from odoo import api, fields, models


class SarabunStepRecipient(models.Model):
    _name = "sarabun.step.recipient"
    _description = "Sarabun Step Recipient (per-person read tracking)"
    _order = "id"

    step_id = fields.Many2one(
        "sarabun.routing.step", required=True, ondelete="cascade", index=True
    )
    document_id = fields.Many2one(
        related="step_id.document_id", store=True, index=True, string="Document"
    )
    user_id = fields.Many2one("res.users", required=True, index=True, string="Recipient")
    employee_id = fields.Many2one(
        "hr.employee", compute="_compute_employee", store=True, string="บุคลากร"
    )
    received_date = fields.Datetime(string="วันที่ได้รับ", readonly=True)
    read_date = fields.Datetime(string="วันที่เปิดอ่าน", readonly=True)
    # phase-2 seam (รอการส่งต่อ) — not set anywhere in v1.
    forwarded = fields.Boolean(string="รอการส่งต่อ", default=False)
    read_state = fields.Selection(
        selection=[
            ("unread", "รอการเปิดอ่าน"),
            ("read", "เปิดอ่านแล้ว"),
            ("forwarded", "รอการส่งต่อ"),
        ],
        compute="_compute_read_state",
        store=True,
        string="สถานะการอ่าน",
    )

    _sql_constraints = [
        ("step_user_uniq", "unique(step_id, user_id)",
         "A recipient row must be unique per user per step."),
    ]

    @api.depends("user_id")
    def _compute_employee(self):
        for rec in self:
            rec.employee_id = rec.user_id.employee_id

    @api.depends("read_date", "forwarded")
    def _compute_read_state(self):
        for rec in self:
            if rec.forwarded:
                rec.read_state = "forwarded"
            elif rec.read_date:
                rec.read_state = "read"
            else:
                rec.read_state = "unread"
