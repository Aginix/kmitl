from odoo import api, fields, models, modules
from odoo.tools import html2plaintext


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def get_my_todos(self, res_model=False, limit=100):
        """List payload for the Discuss Todo page: the current user's open Todos
        as records (capped at ``limit``), earliest deadline first, each carrying
        its source-app icon and the detail fields the list renders.

        Reuses ``_my_todo_count_domain`` (from mail_activity_todo) so the page,
        the systray badge and the Todo app all select the same Todos. Pass
        ``res_model`` to drill into a single source app (matching a sidebar
        group); ``total_count`` then reflects that app, staying consistent with
        the sidebar group badge.
        """
        Activity = self.env["mail.activity"]
        domain = self._my_todo_count_domain()
        if res_model:
            domain = domain + [("res_model", "=", res_model)]
        total = Activity.search_count(domain)
        activities = Activity.search(
            domain, limit=limit, order="date_deadline asc, id desc"
        )

        # Resolve each source model's app icon once, not per record.
        icons = {}

        def model_icon(model_name):
            if model_name not in icons:
                icon = False
                try:
                    icon_module = self.env[model_name]._original_module
                    icon = icon_module and modules.module.get_module_icon(icon_module)
                except Exception:  # never let an icon edge case blank the panel
                    icon = False
                icons[model_name] = icon or False
            return icons[model_name]

        todos = [
            {
                "id": act.id,
                "summary": (
                    act.summary
                    or act.res_name
                    or act.activity_type_id.display_name
                    or ""
                ),
                "res_name": act.res_name or "",
                "res_model": act.res_model,
                "res_id": act.res_id,
                # sudo: regular users cannot read ir.model (non-sensitive
                # metadata); without it the whole payload raises AccessError for
                # non-admins and the Discuss list shows nothing.
                "app": act.res_model_id.sudo().display_name or "",
                "icon": model_icon(act.res_model) if act.res_model else False,
                "activity_type": act.activity_type_id.display_name or "",
                "todo_category": act.todo_category,
                "assigned": act.user_id.display_name or "",
                "note": html2plaintext(act.note)[:160] if act.note else "",
                "date_deadline": (
                    fields.Date.to_string(act.date_deadline)
                    if act.date_deadline
                    else False
                ),
                "state": act.state,
                "action_links": act._get_todo_action_links(),
            }
            for act in activities
        ]
        return {
            "todos": todos,
            "total_count": total,
        }
