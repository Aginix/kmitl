/** @odoo-module **/

import { registry } from "@web/core/registry";

// The unified mail_activity_todo bell supersedes the OCA base_tier_validation
// ReviewerMenu — one inbox for every pending action across every module.
// Dependency on "review_systray_service" (owned by base_tier_validation)
// guarantees this runs after the item is added, so remove() hits.
registry.category("services").add("base_tier_validation_todo.hide_reviewer_menu", {
    dependencies: ["systray_service", "review_systray_service"],
    start() {
        const systray = registry.category("systray");
        if (systray.contains("base_tier_validation.ReviewerMenu")) {
            systray.remove("base_tier_validation.ReviewerMenu");
        }
    },
});
