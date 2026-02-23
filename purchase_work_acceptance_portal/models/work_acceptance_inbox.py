# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WorkAcceptanceInbox(models.Model):
    """Per-user inbox for work acceptance notifications."""

    _name = "work.acceptance.inbox"
    _description = "Work Acceptance Inbox"
    _order = "create_date desc"

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        index=True,
        ondelete="cascade",
    )
    work_acceptance_id = fields.Many2one(
        "work.acceptance",
        string="Work Acceptance",
        required=True,
        index=True,
        ondelete="cascade",
    )
    is_read = fields.Boolean(
        string="Read",
        default=False,
        index=True,
    )
    message = fields.Html(string="Message")

    _sql_constraints = [
        (
            "unique_user_wa",
            "unique(user_id, work_acceptance_id)",
            "Duplicate inbox entry for user and work acceptance",
        ),
    ]

    def action_mark_read(self):
        self.write({"is_read": True})
        self._notify_updated()

    def action_mark_unread(self):
        self.write({"is_read": False})
        self._notify_updated()

    def _notify_updated(self):
        for rec in self:
            self.env["bus.bus"]._sendone(
                rec.user_id.partner_id,
                "work_acceptance/inbox",
                {"refresh": True},
            )
