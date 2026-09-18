/** @odoo-module **/

import {NavBar} from "@web/webclient/navbar/navbar";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {patch} from "web.utils";

patch(NavBar.prototype, "web_apps_menu_favorite.navbar", {
    setup() {
        this._super();
        this.appsMenuFavoriteOrm = useService("orm");
    },

    // Pins favorites into their own bucket on top of web_apps_menu_group's
    // grouping; they are removed from the regular buckets so an app never
    // shows up twice in the grid.
    getGroupedApps(apps) {
        const favorites = apps.filter((app) => app.isFavorite);
        const groups = this._super(apps.filter((app) => !app.isFavorite));
        if (favorites.length) {
            groups.unshift({
                id: "favorite",
                name: _t("Favorite"),
                apps: favorites,
            });
        }
        return groups;
    },

    // Mutates the shared menusData entry in place (same object every
    // `menuService.getApps()` call returns), then forces a re-render.
    async toggleFavoriteApp(app) {
        app.isFavorite = await this.appsMenuFavoriteOrm.call(
            "ir.ui.menu",
            "action_toggle_favorite",
            [app.id]
        );
        this.render();
    },
});
