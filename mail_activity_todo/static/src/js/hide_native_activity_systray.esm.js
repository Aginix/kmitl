/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * The unified Todo systray supersedes Odoo's native Activities menu (which is
 * user_id-only and cannot show role-in-unit group Todos). Remove the native
 * bell so there is a single inbox. This service depends on "systray_service",
 * which adds "mail.ActivityMenu" on start, so it runs afterwards and the
 * removal sticks.
 */
registry.category("services").add("mail_activity_todo.hide_native_activity_menu", {
    dependencies: ["systray_service"],
    start() {
        const systray = registry.category("systray");
        if (systray.contains("mail.ActivityMenu")) {
            systray.remove("mail.ActivityMenu");
        } else {
            // Fail loudly if a future mail refactor renames/relocates the key,
            // so the native bell doesn't silently reappear next to ours.
            console.warn(
                "mail_activity_todo: 'mail.ActivityMenu' systray item not found; " +
                    "the native Activities menu could not be hidden."
            );
        }
    },
});
