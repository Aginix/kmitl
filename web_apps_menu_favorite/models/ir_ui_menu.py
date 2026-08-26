from odoo import api, fields, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    favorite_user_ids = fields.Many2many(
        "res.users",
        "web_apps_menu_favorite_rel",
        "menu_id",
        "user_id",
        string="Favorited By",
        help="Users who pinned this app to the top of their Apps grid.",
    )

    def action_toggle_favorite(self):
        """Toggle the current user's favorite status for this app.

        Runs as sudo since a regular user only has read access to
        ir.ui.menu; the mutation is safely scoped to adding/removing
        the acting user themselves.
        """
        self.ensure_one()
        user = self.env.user
        is_favorite = user in self.favorite_user_ids
        if is_favorite:
            self.sudo().favorite_user_ids = [(3, user.id)]
        else:
            self.sudo().favorite_user_ids = [(4, user.id)]
        return not is_favorite

    @api.model
    def load_menus(self, debug):
        # See web_apps_menu_group's load_menus override for why this must
        # be injected here (not just load_web_menus): it's what gets
        # hashed into the cached /web/webclient/load_menus/<hash> URL.
        menus = super().load_menus(debug)
        app_ids = [
            mid
            for mid, menu in menus.items()
            if mid != "root" and menu.get("id") == menu.get("app_id")
        ]
        if not app_ids:
            return menus
        user = self.env.user
        extra = {
            app.id: {"isFavorite": user in app.favorite_user_ids}
            for app in self.sudo().browse(app_ids)
        }
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
            web_menu["isFavorite"] = menu.get("isFavorite", False)
        return web_menus
