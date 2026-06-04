from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def get_my_todo_count(self, limit=10):
        """Systray payload: count + a few open Todos for the current user.

        "Open" = addressed to me (is_my_todo) and not yet read by me. Done Todos
        no longer exist (they are deleted on feedback), so there is no done filter.
        """
        Activity = self.env["mail.activity"]
        domain = [("is_my_todo", "=", True), ("is_read_by_me", "=", False)]
        total = Activity.search_count(domain)
        todos = Activity.search(domain, order="date_deadline asc, id desc", limit=limit)
        return {
            "total_count": total,
            "form_view_id": self.env.ref("kmitl_todo.view_my_todo_form").id,
            "todos": [
                {
                    "id": a.id,
                    "summary": a.summary or a.activity_type_id.display_name or a.res_name,
                    "res_name": a.res_name or "",
                    "res_model": a.res_model,
                    "res_id": a.res_id,
                    "date": a.date_deadline and a.date_deadline.strftime("%d/%m/%Y") or "",
                    "category": a.todo_category or "",
                    "icon": a.icon or "fa-thumb-tack",
                    "state": a.state,
                }
                for a in todos
            ],
        }
