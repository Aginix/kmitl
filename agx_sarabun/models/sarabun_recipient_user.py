# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SarabunRecipientUser(models.Model):
    """Per-user tracking for document recipients.

    Created when a routing line is added, recording which users are
    resolved for each routing step. Adopted by document.recipient
    when the document is sent.
    """

    _name = "sarabun.recipient.user"
    _description = "Sarabun Recipient User Tracking"
    _order = "sequence, id"

    routing_line_id = fields.Many2one(
        comodel_name="sarabun.routing.line",
        string="Routing Line",
        ondelete="set null",
        index=True,
    )
    recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        string="Recipient",
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        index=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    resolution_reason = fields.Selection(
        selection=[
            ("direct", "Direct User"),
            ("dept_officer", "Department Officer"),
            ("dept_manager", "Department Manager"),
            ("role_static", "Static Role Assignment"),
            ("role_dynamic", "Dynamic Role Resolution"),
        ],
        string="Resolution Reason",
    )
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("read", "Read"),
            ("actioned", "Actioned"),
        ],
        string="Status",
        default="pending",
        required=True,
    )
    read_date = fields.Datetime(
        string="Read Date",
        readonly=True,
    )
    actioned_date = fields.Datetime(
        string="Actioned Date",
        readonly=True,
    )

    # === Computed Fields ===
    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        compute="_compute_document_id",
        store=True,
        index=True,
    )
    recipient_type = fields.Selection(
        selection=[
            ("user", "User"),
            ("department", "Department"),
            ("role", "Role/Position"),
        ],
        string="Recipient Type",
        compute="_compute_recipient_type",
        store=True,
    )

    _sql_constraints = [
        (
            "unique_routing_line_user",
            "UNIQUE(routing_line_id, user_id)",
            "Each user can only appear once per routing line.",
        ),
    ]

    @api.depends("recipient_id.document_id", "routing_line_id.document_id")
    def _compute_document_id(self):
        for record in self:
            record.document_id = (
                record.recipient_id.document_id
                or record.routing_line_id.document_id
            )

    @api.depends("recipient_id.recipient_type", "routing_line_id.recipient_type")
    def _compute_recipient_type(self):
        for record in self:
            record.recipient_type = (
                record.recipient_id.recipient_type
                if record.recipient_id
                else record.routing_line_id.recipient_type
                if record.routing_line_id
                else False
            )

    def mark_as_read(self):
        """Mark this user's tracking record as read."""
        now = fields.Datetime.now()
        for record in self:
            if record.state == "pending":
                record.write({
                    "state": "read",
                    "read_date": now,
                })

    def mark_as_actioned(self):
        """Mark this user's tracking record as actioned."""
        now = fields.Datetime.now()
        for record in self:
            if record.state in ("pending", "read"):
                vals = {
                    "state": "actioned",
                    "actioned_date": now,
                }
                if not record.read_date:
                    vals["read_date"] = now
                record.write(vals)
