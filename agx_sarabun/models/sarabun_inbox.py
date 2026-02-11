# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SarabunInbox(models.Model):
    """Per-user inbox read/unread status, independent of recipient state."""

    _name = "sarabun.inbox"
    _description = "Sarabun Inbox"
    _order = "create_date desc"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        index=True,
        ondelete="cascade",
    )
    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
        index=True,
        ondelete="cascade",
    )
    is_read = fields.Boolean(
        string="Read",
        default=False,
        index=True,
    )

    _sql_constraints = [
        (
            "unique_user_document",
            "unique(user_id, document_id)",
            "Duplicate inbox entry for user and document",
        ),
    ]

    def action_mark_read(self):
        """Mark inbox entries as read"""
        self.write({"is_read": True})
        self._notify_inbox_updated()

    def action_mark_unread(self):
        """Mark inbox entries as unread"""
        self.write({"is_read": False})
        self._notify_inbox_updated()

    def _notify_inbox_updated(self):
        """Send bus notification to refresh systray"""
        for user_id in self.mapped("user_id").ids:
            partner = self.env["res.users"].browse(user_id).partner_id
            self.env["bus.bus"]._sendone(
                partner,
                "sarabun_inbox/updated",
                {"refresh": True},
            )
