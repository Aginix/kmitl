from odoo import api, fields, models, modules


class ResUsers(models.Model):
    _inherit = "res.users"

    kmitl_role_ids = fields.Many2many(
        "res.users.role",
        compute="_compute_kmitl_role_ids",
        compute_sudo=True,
        string="Todo Roles",
        help="Roles the user holds, exposed without ERP-manager rights so Todo "
        "routing (inbox domain + record rules) can read them.",
    )

    @api.depends("role_ids")
    def _compute_kmitl_role_ids(self):
        for user in self:
            user.kmitl_role_ids = user.sudo().role_ids.ids

    def _my_todo_count_domain(self):
        return [
            ("is_my_todo", "=", True),
            ("is_read_by_me", "=", False),
            ("todo_category", "!=", False),
        ]

    def get_my_todo_count(self):
        """Systray payload: open Todos grouped by source model with per-model
        icon and overdue/today/planned counts.

        Uses read_group aggregates rather than materialising every record (no
        per-record ``state`` recompute), so it stays cheap on large role-in-unit
        fan-out.
        """
        Activity = self.env["mail.activity"]
        base = self._my_todo_count_domain()
        today = fields.Date.to_string(fields.Date.context_today(self))
        buckets = {
            "overdue_count": [("date_deadline", "<", today)],
            "today_count": [("date_deadline", "=", today)],
            "planned_count": [("date_deadline", ">", today)],
        }
        groups = {}

        def ensure(model_id, model_name):
            grp = groups.get(model_id)
            if grp is None:
                model = self.env["ir.model"].browse(model_id).model
                icon = False
                try:
                    icon_module = self.env[model]._original_module
                    icon = icon_module and modules.module.get_module_icon(icon_module)
                except Exception:  # never let an icon edge case blank the systray
                    icon = False
                grp = groups[model_id] = {
                    "model": model,
                    "model_id": model_id,
                    "name": model_name,
                    "icon": icon or False,
                    "total_count": 0,
                    "overdue_count": 0,
                    "today_count": 0,
                    "planned_count": 0,
                }
            return grp

        def count_of(rg):
            return rg.get("__count") or rg.get("res_model_id_count") or 0

        for rg in Activity.read_group(base, ["res_model_id"], ["res_model_id"]):
            if not rg.get("res_model_id"):
                continue
            model_id, model_name = rg["res_model_id"]
            ensure(model_id, model_name)["total_count"] = count_of(rg)
        for key, dom in buckets.items():
            for rg in Activity.read_group(
                base + dom, ["res_model_id"], ["res_model_id"]
            ):
                if not rg.get("res_model_id"):
                    continue
                model_id, model_name = rg["res_model_id"]
                ensure(model_id, model_name)[key] = count_of(rg)

        total = sum(g["total_count"] for g in groups.values())
        return {
            "total_count": total,
            "tree_view_id": self.env.ref("kmitl_todo.view_my_todo_tree").id,
            "form_view_id": self.env.ref("kmitl_todo.view_my_todo_form").id,
            "groups": sorted(groups.values(), key=lambda g: g["name"] or ""),
        }
