from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_workflow_event(self, users, subject, body):
        """Post a workflow-event notification visible only in the workflow systray.

        - Does NOT appear in Discuss Inbox (notification_type='workflow', not 'inbox')
        - Does NOT appear in the Todo inbox (uses mail.message, not mail.activity)
        - Skips users who have disabled workflow notifications in Preferences
        - Sends to every user in the recordset regardless of follower status

        Args:
            users: res.users recordset — recipients
            subject: str — short event description shown in the systray popover
            body: str — optional longer description (HTML allowed)
        """
        if not users:
            return
        enabled_users = users.filtered("workflow_notification_enabled")
        if not enabled_users:
            return

        for record in self:
            msg = record.message_post(
                body=body or subject,
                subject=subject,
                message_type="notification",
                subtype_xmlid="mail.mt_note",
                partner_ids=[],
            )
            # Repoint the notification rows to 'workflow' so Discuss Inbox
            # (which filters notification_type='inbox') never sees them.
            notif_vals = []
            for user in enabled_users:
                notif_vals.append(
                    {
                        "mail_message_id": msg.id,
                        "res_partner_id": user.partner_id.id,
                        "notification_type": "workflow",
                        "notification_status": "sent",
                        "is_read": False,
                    }
                )
            if notif_vals:
                self.env["mail.notification"].sudo().create(notif_vals)
                record._workflow_notify_bus(enabled_users)

    @api.model
    def _workflow_notify_bus(self, users):
        """Ping recipients' bus channels so their systray badge refreshes live."""
        for user in users:
            self.env["bus.bus"]._sendone(
                user.partner_id,
                "mail_workflow_notification/updated",
                {"refresh": True},
            )

    @api.model
    def action_mark_workflow_notifications_read(self):
        """Mark all unread workflow notifications for the current user as read."""
        partner = self.env.user.partner_id
        notifs = self.env["mail.notification"].sudo().search(
            [
                ("res_partner_id", "=", partner.id),
                ("notification_type", "=", "workflow"),
                ("is_read", "=", False),
            ]
        )
        notifs.write({"is_read": True})
        self.env["bus.bus"]._sendone(
            partner,
            "mail_workflow_notification/updated",
            {"refresh": True},
        )
        return True

    @api.model
    def get_workflow_notifications(self):
        """Return the 10 most recent unread workflow notifications for the systray."""
        partner = self.env.user.partner_id
        notifs = (
            self.env["mail.notification"]
            .sudo()
            .search(
                [
                    ("res_partner_id", "=", partner.id),
                    ("notification_type", "=", "workflow"),
                    ("is_read", "=", False),
                ],
                order="id desc",
                limit=10,
            )
        )
        unread_count = (
            self.env["mail.notification"]
            .sudo()
            .search_count(
                [
                    ("res_partner_id", "=", partner.id),
                    ("notification_type", "=", "workflow"),
                    ("is_read", "=", False),
                ]
            )
        )
        items = []
        for notif in notifs:
            msg = notif.mail_message_id
            items.append(
                {
                    "id": notif.id,
                    "subject": msg.subject or "",
                    "body": msg.body or "",
                    "res_model": msg.model or "",
                    "res_id": msg.res_id or 0,
                    "record_name": msg.record_name or "",
                    "date": msg.date.isoformat() if msg.date else "",
                }
            )
        return {"items": items, "unread_count": unread_count}
