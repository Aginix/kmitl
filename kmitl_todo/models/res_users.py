from odoo import models, modules


class ResUsers(models.Model):
    _inherit = "res.users"

    def get_my_todo_count(self, limit_per_group=10):
        """Systray payload: open Todos for the current user, grouped by source
        model (native Activities-menu style) with per-model icon and count.

        "Open" = addressed to me (is_my_todo) and not yet read by me; done Todos
        no longer exist (deleted on feedback), so there is no done filter.
        """
        Activity = self.env["mail.activity"]
        activities = Activity.search(
            [("is_my_todo", "=", True), ("is_read_by_me", "=", False)],
            order="date_deadline asc, id desc",
        )
        groups = {}
        for act in activities:
            model = act.res_model
            group = groups.get(model)
            if group is None:
                try:
                    icon_module = self.env[model]._original_module
                except KeyError:
                    icon_module = False
                group = groups[model] = {
                    "model": model,
                    "model_id": act.res_model_id.id,
                    "name": act.res_model_id.name or model,
                    "icon": (icon_module and modules.module.get_module_icon(icon_module))
                    or False,
                    "count": 0,
                    "todos": [],
                }
            group["count"] += 1
            if len(group["todos"]) < limit_per_group:
                group["todos"].append(
                    {
                        "id": act.id,
                        "summary": act.summary
                        or act.activity_type_id.display_name
                        or act.res_name,
                        "res_name": act.res_name or "",
                        "date": act.date_deadline
                        and act.date_deadline.strftime("%d/%m/%Y")
                        or "",
                        "state": act.state,
                        "icon": act.icon or "fa-thumb-tack",
                    }
                )
        return {
            "total_count": len(activities),
            "form_view_id": self.env.ref("kmitl_todo.view_my_todo_form").id,
            "groups": sorted(groups.values(), key=lambda g: g["name"]),
        }
