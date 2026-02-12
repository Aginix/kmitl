# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SarabunRecipientUser(models.Model):
    """Per-user tracking for document recipients.

    Created as a snapshot when a recipient is activated, recording which
    users were resolved at that point in time and tracking individual
    read/action states.
    """

    _name = "sarabun.recipient.user"
    _description = "Sarabun Recipient User Tracking"
    _order = "sequence, id"

    recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        string="Recipient",
        required=True,
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

    # === Related Fields (stored for performance) ===
    document_id = fields.Many2one(
        related="recipient_id.document_id",
        store=True,
        index=True,
    )
    recipient_type = fields.Selection(
        related="recipient_id.recipient_type",
        store=True,
    )

    _sql_constraints = [
        (
            "unique_recipient_user",
            "UNIQUE(recipient_id, user_id)",
            "Each user can only appear once per recipient.",
        ),
    ]

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
