# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def get_sarabun_inbox_count(self):
        """
        Return unread sarabun documents grouped by document type.
        Used by the systray notification widget.
        """
        Recipient = self.env["sarabun.document.recipient"]
        user = self.env.user

        # Build domain for recipients the current user can access
        # and that are in 'new' state (unread/unactioned)
        recipients = Recipient.sudo().search([
            ("state", "=", "new"),
            ("document_id.state", "=", "sent"),
        ])

        # Filter to only recipients this user can access
        accessible_recipients = recipients.filtered(
            lambda r: r._can_user_access(user)
        )

        # Group by document type
        result = []
        type_groups = {}

        for recipient in accessible_recipients:
            doc = recipient.document_id
            doc_type = doc.document_type_id

            type_key = doc_type.id if doc_type else 0
            if type_key not in type_groups:
                type_groups[type_key] = {
                    "id": type_key,
                    "name": doc_type.name if doc_type else "Other",
                    "count": 0,
                    "recipient_ids": [],
                }
            type_groups[type_key]["count"] += 1
            type_groups[type_key]["recipient_ids"].append(recipient.id)

        result = list(type_groups.values())

        return {
            "groups": result,
            "total_count": len(accessible_recipients),
        }
