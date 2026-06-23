# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def review_user_count(self):
        """Hide work.acceptance from the tier-validation systray review list:
        committee review is surfaced through mail_activity_todo instead, so
        listing it here would double-count the same pending work.
        """
        result = super().review_user_count()
        return [r for r in result if r.get("model") != "work.acceptance"]

    @api.model
    def get_my_todos(self, res_model=False, limit=100):
        """Attach portal/PO action links to each Todo payload.

        Action links are a feature of this module (committee review needs
        per-user-tokened portal URLs); keeping the attachment here rather than
        in ``mail_activity_todo_discuss`` lets the base modules stay agnostic.
        """
        result = super().get_my_todos(res_model=res_model, limit=limit)
        Activity = self.env["mail.activity"]
        for todo in result.get("todos", []):
            act = Activity.browse(todo["id"])
            todo["action_links"] = (
                act._get_todo_action_links() if act.exists() else []
            )
        return result
