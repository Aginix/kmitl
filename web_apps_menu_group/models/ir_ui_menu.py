from odoo import api, fields, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    apps_menu_group_id = fields.Many2one(
        "web.apps.menu.group",
        string="Apps Menu Group",
        ondelete="set null",
        help="Only used on top-level (app) menus: groups apps together in "
        "the backend Apps grid menu.",
    )

    @api.model
    def load_menus(self, debug):
        # NOTE: the webclient hashes the output of `load_menus` (not
        # `load_web_menus`) to build the 1-year-cached
        # `/web/webclient/load_menus/<hash>` URL (see `web/models/ir_http.py`
        # `session_info()`). Group data must be injected here, not only in
        # `load_web_menus`, otherwise editing an assignment never changes the
        # hash and browsers keep serving the stale ungrouped payload.
        menus = super().load_menus(debug)
        app_ids = [
            mid
            for mid, menu in menus.items()
            if mid != "root" and menu.get("id") == menu.get("app_id")
        ]
        if not app_ids:
            return menus
        extra = {}
        for app in self.sudo().browse(app_ids):
            group = app.apps_menu_group_id
            extra[app.id] = {
                "appsMenuGroupId": group.id,
                "appsMenuGroupName": group.name or False,
                "appsMenuGroupSequence": group.sequence if group else False,
            }
        # Build a new top-level dict instead of mutating the nested dicts
        # owned by the ormcache'd `menus` object returned by `super()`.
        return {
            mid: ({**menu, **extra[mid]} if mid in extra else menu)
            for mid, menu in menus.items()
        }

    def load_web_menus(self, debug):
        web_menus = super().load_web_menus(debug)
        menus = self.load_menus(debug)
        for mid, web_menu in web_menus.items():
            menu = menus.get(mid)
            if not menu:
                continue
            web_menu["groupId"] = menu.get("appsMenuGroupId", False)
            web_menu["groupName"] = menu.get("appsMenuGroupName", False)
            web_menu["groupSequence"] = menu.get("appsMenuGroupSequence", False)
        return web_menus
