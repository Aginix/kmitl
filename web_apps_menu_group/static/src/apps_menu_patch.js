/** @odoo-module **/

import {NavBar} from "@web/webclient/navbar/navbar";
import {patch} from "web.utils";

// Patched onto NavBar (not the AppsMenu component) because the apps grid
// markup in `web.NavBar.AppsMenu` is slot content rendered in NavBar's own
// scope — `web_responsive` itself patches `NavBar.prototype.getWebIconData`
// for the same reason.
patch(NavBar.prototype, "web_apps_menu_group.navbar", {
    /**
     * Bucket apps by their assigned group, sorted by group sequence.
     * Apps without a group are appended last, in their original order,
     * without a header — so the grid is visually unchanged until an admin
     * actually configures groups.
     *
     * @param {Array} apps
     * @returns {Array<{id: (number|string), name: (string|false), apps: Array}>}
     */
    getGroupedApps(apps) {
        const groups = new Map();
        const ungrouped = [];
        for (const app of apps) {
            if (!app.groupId) {
                ungrouped.push(app);
                continue;
            }
            if (!groups.has(app.groupId)) {
                groups.set(app.groupId, {
                    id: app.groupId,
                    name: app.groupName,
                    sequence: app.groupSequence || 0,
                    apps: [],
                });
            }
            groups.get(app.groupId).apps.push(app);
        }
        const result = [...groups.values()].sort((a, b) => a.sequence - b.sequence);
        if (ungrouped.length) {
            result.push({id: "ungrouped", name: false, apps: ungrouped});
        }
        return result;
    },
});
