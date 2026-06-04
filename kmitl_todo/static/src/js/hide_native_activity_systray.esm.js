/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * The unified Todo systray supersedes Odoo's native Activities menu (which is
 * user_id-only and cannot show role-in-unit group Todos). Remove the native
 * bell so there is a single inbox. This service depends on "systray_service",
 * which adds "mail.ActivityMenu" on start, so it runs afterwards and the
 * removal sticks.
 */
registry.category("services").add("kmitl_todo.hide_native_activity_menu", {
    dependencies: ["systray_service"],
    start() {
        registry.category("systray").remove("mail.ActivityMenu");
    },
});
