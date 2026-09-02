from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def action_toggle_favorite(self):
        """Toggle the current user's favorite status for this app.

        Written from the res.users side on purpose: writing the same m2m
        through ir.ui.menu would go through IrUiMenu.write(), which calls
        clear_caches() and flushes the whole registry ormcache for every
        user. sudo() because a regular user cannot write on res.users.
        """
        self.ensure_one()
        user = self.env.user
        is_favorite = self in user.sudo().favorite_menu_ids
        user.sudo().favorite_menu_ids = [(3 if is_favorite else 4, self.id)]
        return not is_favorite

    @api.model
    def load_menus(self, debug):
        # See web_apps_menu_group's load_menus override for why this must
        # be injected here (not just load_web_menus): it's what gets
        # hashed into the cached /web/webclient/load_menus/<hash> URL.
        menus = super().load_menus(debug)
        favorite_ids = set(self.env.user.sudo().favorite_menu_ids.ids)
        if not favorite_ids:
            return menus
        return {
            mid: ({**menu, "isFavorite": True} if mid in favorite_ids else menu)
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
