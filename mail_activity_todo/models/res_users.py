from odoo import api, fields, models, modules, tools


class ResUsers(models.Model):
    _inherit = "res.users"

    def _my_todo_count_domain(self):
        # Fork A (ADR-0006): the inbox is every open activity assigned to me,
        # minus the ones I've dismissed with Mark as Read. Category is not a gate.
        return [
            ("is_my_todo", "=", True),
            ("is_read_by_me", "=", False),
        ]

    def _my_read_todo_domain(self):
        # History (ADR-0003): the inbox's read complement — my Todos that I have
        # dismissed with Mark as Read. Same recipient base, flipped read flag.
        return [
            ("is_my_todo", "=", True),
            ("is_read_by_me", "=", True),
        ]

    @api.model
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
        icons = {}

        def ensure(model_id, model_name):
            grp = groups.get(model_id)
            if grp is None:
                # sudo: regular users have no read access to ir.model, but the
                # technical model name is non-sensitive metadata (read_group
                # already resolves res_model_id names via sudo). Without this the
                # whole payload raises AccessError for non-admins and the systray
                # / Discuss panel silently show nothing.
                model = self.env["ir.model"].sudo().browse(model_id).model
                grp = groups[model_id] = {
                    "model": model,
                    "model_id": model_id,
                    "name": model_name,
                    "icon": self._todo_model_icon(model, icons),
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
            "tree_view_id": self.env.ref("mail_activity_todo.view_my_todo_tree").id,
            "form_view_id": self.env.ref("mail_activity_todo.view_my_todo_form").id,
            "groups": sorted(groups.values(), key=lambda g: g["name"] or ""),
        }

    def _todo_model_icon(self, model_name, cache):
        """Source model's app icon, resolved once per model and memoised in
        ``cache``."""
        if model_name not in cache:
            icon = False
            try:
                icon = self._todo_resolve_icon(model_name)
            except (KeyError, AttributeError):
                # model not in registry or missing _original_module
                icon = False
            cache[model_name] = icon or False
        return cache[model_name]

    @tools.ormcache("model_name")
    def _todo_resolve_icon(self, model_name):
        """Resolve the app icon for *model_name* by tracing
        action → menu → root menu → ``web_icon``.

        Picks the root menu of the model's own app (see ``_pick_root_icon``),
        so a model that a second app also links to keeps its own icon.  The
        root's ``web_icon`` already carries any KMITL re-skin.  Falls back to
        the defining module's ``icon.png``.
        """
        icon_module = self.env[model_name]._original_module

        # 1. Find act_window actions targeting this model
        actions = (
            self.env["ir.actions.act_window"]
            .sudo()
            .search([("res_model", "=", model_name)])
        )
        if actions:
            # 2. Find menus that reference those actions
            action_refs = ["ir.actions.act_window,%d" % a_id for a_id in actions.ids]
            Menu = (
                self.env["ir.ui.menu"]
                .sudo()
                .with_context(**{"ir.ui.menu.full_list": True})
            )
            menus = Menu.search([("action", "in", action_refs)])
            if menus:
                # 3. Walk parent_path to collect root menu ids
                root_ids = set()
                for menu in menus:
                    if menu.parent_path:
                        root_ids.add(int(menu.parent_path.strip("/").split("/")[0]))
                # search (not browse) so roots come back in sequence, id order
                roots = Menu.search(
                    [("id", "in", list(root_ids)), ("web_icon", "!=", False)]
                )
                icon = self._pick_root_icon(roots, icon_module)
                if icon:
                    return icon

        # 4. Fallback: defining module's own icon.png
        return modules.module.get_module_icon(icon_module) if icon_module else False

    def _pick_root_icon(self, roots, icon_module):
        """Pick the ``web_icon`` of the root that owns the model's app.

        Roots are ranked by how much of their XML-ID module the model's
        defining module shares, so ``procurement.plan`` resolves to the
        Procurement Plan root rather than the Budget root that also links to
        it.  Ties keep the menus' own ``sequence, id`` order.  Validate the
        icon file exists on disk so we never return a path to a missing image.
        """
        xmlids = roots._get_external_ids()

        def _affinity(root):
            # longest XML-ID module that the model's module extends
            best = 0
            for xmlid in xmlids.get(root.id) or []:
                mod = xmlid.split(".")[0]
                if icon_module and (
                    icon_module == mod or icon_module.startswith("%s_" % mod)
                ):
                    best = max(best, len(mod))
            return best

        def _valid_icon(root):
            parts = (root.web_icon or "").split(",")
            if len(parts) != 2:
                return None
            mod, path = parts[0].strip(), parts[1].strip()
            if modules.module.get_module_resource(mod, *path.split("/")):
                return "/%s/%s" % (mod, path)
            return None

        # sorted() is stable, so equally-related roots keep the search order
        for root in sorted(roots, key=lambda r: -_affinity(r)):
            icon = _valid_icon(root)
            if icon:
                return icon
        return False
