# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def get_wa_inbox_count(self):
        """Return unread work acceptances for the current user. Used by systray."""
        entries = self.env["work.acceptance.inbox"].search(
            [("user_id", "=", self.env.user.id), ("is_read", "=", False)],
            order="create_date desc",
        )
        if not entries:
            return {"items": [], "total_count": 0}

        employee = self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id)], limit=1
        )

        # Batch-fetch completed committees to avoid N+1 queries
        done_wa_ids = set()
        if employee:
            done_wa_ids = set(
                self.env["work.acceptance.committee"]
                .search([
                    ("wa_id", "in", entries.mapped("work_acceptance_id").ids),
                    ("employee_id", "=", employee.id),
                    ("status", "in", ("accept", "accept_conditionally", "not_accept", "other")),
                ])
                .mapped("wa_id")
                .ids
            )

        seen = set()
        items = []
        for entry in entries:
            wa = entry.work_acceptance_id
            if wa.id in done_wa_ids:
                continue
            if wa.id not in seen:
                seen.add(wa.id)
                items.append({
                    "id": entry.id,
                    "wa_id": wa.id,
                    "name": wa.name,
                    "wa_url": entry.wa_url or "",
                    "order_url": entry.order_url or "",
                })

        return {"items": items, "total_count": len(items)}

    @api.model
    def review_user_count(self):
        """Exclude work.acceptance from tier validation systray — use custom WaSystray instead."""
        result = super().review_user_count()
        return [r for r in result if r.get("model") != "work.acceptance"]

    @api.model
    def get_wa_inbox_all(self):
        """Return all work acceptances for the current user regardless of read status."""
        entries = self.env["work.acceptance.inbox"].search(
            [("user_id", "=", self.env.user.id)],
            order="create_date desc",
        )
        if not entries:
            return {"items": [], "total_count": 0}

        employee = self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id)], limit=1
        )

        done_wa_ids = set()
        if employee:
            done_wa_ids = set(
                self.env["work.acceptance.committee"]
                .search([
                    ("wa_id", "in", entries.mapped("work_acceptance_id").ids),
                    ("employee_id", "=", employee.id),
                    ("status", "in", ("accept", "accept_conditionally", "not_accept", "other")),
                ])
                .mapped("wa_id")
                .ids
            )

        seen = set()
        items = []
        for entry in entries:
            wa = entry.work_acceptance_id
            if wa.id in done_wa_ids:
                continue
            if wa.id not in seen:
                seen.add(wa.id)
                items.append({
                    "id": entry.id,
                    "wa_id": wa.id,
                    "name": wa.name,
                    "wa_url": entry.wa_url or "",
                    "order_url": entry.order_url or "",
                })

        return {"items": items, "total_count": len(items)}

    @api.model
    def mark_all_wa_read(self):
        """Mark all unread inbox entries as read for the current user."""
        self.env["work.acceptance.inbox"].search([
            ("user_id", "=", self.env.user.id),
            ("is_read", "=", False),
        ]).action_mark_read()
