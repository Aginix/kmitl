from odoo import api, fields, models, modules


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def get_my_todos(self, limit=100):
        """List payload for the Discuss Todo panel: the current user's open
        Todos as records (capped at ``limit``), earliest deadline first, each
        carrying its source-app icon.

        Reuses ``_my_todo_count_domain`` (from mail_activity_todo) so the panel
        list, the systray badge and the Todo app all select the same Todos.
        ``total_count`` lets the panel show "View all (N)" when more remain.
        """
        Activity = self.env["mail.activity"]
        domain = self._my_todo_count_domain()
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
                "icon": model_icon(act.res_model) if act.res_model else False,
                "date_deadline": (
                    fields.Date.to_string(act.date_deadline)
                    if act.date_deadline
                    else False
                ),
                "state": act.state,
                "todo_category": act.todo_category,
            }
            for act in activities
        ]
        return {
            "todos": todos,
            "total_count": total,
            "shown_count": len(todos),
        }
