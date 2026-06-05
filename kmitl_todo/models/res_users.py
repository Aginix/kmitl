from odoo import models, modules


class ResUsers(models.Model):
    _inherit = "res.users"

    def get_my_todo_count(self):
        """Systray payload: open Todos for the current user, grouped by source
        model (native Activities-menu style) with per-model icon and
        overdue/today/planned counts.

        "Open" = addressed to me (is_my_todo) and not yet read by me; done Todos
        no longer exist (deleted on feedback), so there is no done filter.
        """
        activities = self.env["mail.activity"].search(
            [("is_my_todo", "=", True), ("is_read_by_me", "=", False)]
        )
        groups = {}
        for act in activities:
            model = act.res_model
            group = groups.get(model)
            if group is None:
                icon = False
                try:
                    icon_module = self.env[model]._original_module
                    icon = icon_module and modules.module.get_module_icon(icon_module)
                except Exception:  # never let an icon edge case blank the systray
                    icon = False
                group = groups[model] = {
                    "model": model,
                    "model_id": act.res_model_id.id,
                    "name": act.res_model_id.name or model,
                    "icon": icon or False,
                    "total_count": 0,
                    "overdue_count": 0,
                    "today_count": 0,
                    "planned_count": 0,
                }
            group["total_count"] += 1
            group["%s_count" % act.state] += 1
        return {
            "total_count": len(activities),
            "tree_view_id": self.env.ref("kmitl_todo.view_my_todo_tree").id,
            "form_view_id": self.env.ref("kmitl_todo.view_my_todo_form").id,
            "groups": sorted(groups.values(), key=lambda g: g["name"]),
        }
