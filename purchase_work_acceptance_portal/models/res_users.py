# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def get_wa_inbox_count(self):
        """Return recent unread work acceptances (up to 10). Used by systray."""
        entries = self.env["work.acceptance.inbox"].search(
            [("user_id", "=", self.env.user.id), ("is_read", "=", False)],
            order="create_date desc",
        )
        seen = set()
        items = []
        for entry in entries:
            wa = entry.work_acceptance_id
            if wa.id not in seen:
                seen.add(wa.id)
                items.append({
                    "id": wa.id,
                    "name": wa.name,
                    "message": entry.message or "",
                })
        return {"items": items[:10], "total_count": len(seen)}
