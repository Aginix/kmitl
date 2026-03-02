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

        employee = self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id)], limit=1
        )

        seen = set()
        items = []
        for entry in entries:
            wa = entry.work_acceptance_id

            if employee:
                committee = self.env["work.acceptance.committee"].search(
                    [
                        ("wa_id", "=", wa.id),
                        ("employee_id", "=", employee.id),
                    ],
                    limit=1,
                )
                if committee and committee.status in ("accept", "not_accept", "other"):
                    continue

            if wa.id not in seen:
                seen.add(wa.id)
                items.append({
                    "id": wa.id,
                    "name": wa.name,
                    "wa_url": entry.wa_url or "",
                    "order_url": entry.order_url or "",
                })

        return {"items": items[:10], "total_count": len(seen)}
