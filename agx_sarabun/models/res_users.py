# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def get_sarabun_inbox_count(self):
        """
        Return recent unread sarabun documents (up to 10).
        Used by the systray notification widget.
        """
        Recipient = self.env["sarabun.document.recipient"]
        user = self.env.user

        # Build domain for recipients the current user can access
        # that are in 'new' state and not yet read (read_date is null)
        recipients = Recipient.sudo().search([
            ("state", "=", "new"),
            ("read_date", "=", False),
            ("document_id.state", "=", "sent"),
        ], order="create_date desc")

        # Filter to only recipients this user can access
        accessible_recipients = recipients.filtered(
            lambda r: r._can_user_access(user)
        )

        # Get unique documents (a document may have multiple recipients)
        seen_docs = set()
        documents = []
        for recipient in accessible_recipients:
            doc = recipient.document_id
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
