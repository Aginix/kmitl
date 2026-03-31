# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    sarabun_email_notification = fields.Boolean(
        string="Sarabun Email Notifications",
        default=True,
        help="Receive email notifications for sarabun document events",
    )

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["sarabun_email_notification"]

    @api.model
    def get_sarabun_inbox_count(self):
        """
        Return recent unread sarabun documents (up to 10).
        Used by the systray notification widget.
        """
        Inbox = self.env["sarabun.inbox"]

        entries = Inbox.search([
            ("user_id", "=", self.env.user.id),
            ("is_read", "=", False),
            ("document_id.state", "in", ["sent", "completed"]),
        ], order="create_date desc")

        # Deduplicate by document
        seen_docs = set()
        documents = []
        for entry in entries:
            doc = entry.document_id
            if doc.id not in seen_docs:
                seen_docs.add(doc.id)
                documents.append({
                    "id": doc.id,
                    "name": doc.name or "Draft",
                    "subject": doc.subject or "",
                    "date": doc.date.strftime("%d/%m/%Y") if doc.date else "",
                    "document_type": doc.document_type_id.name if doc.document_type_id else "",
                })

        return {
            "documents": documents[:10],
            "total_count": len(seen_docs),
        }
