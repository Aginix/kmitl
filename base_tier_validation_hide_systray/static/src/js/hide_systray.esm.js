/** @odoo-module **/

import { registry } from "@web/core/registry";

// Removes the OCA base_tier_validation ReviewerMenu bell from the systray.
// Depending on "review_systray_service" (owned by base_tier_validation)
// guarantees this runs after the item has been added, so remove() hits.
registry.category("services").add("base_tier_validation_hide_systray.hide_reviewer_menu", {
    dependencies: ["review_systray_service"],
    start() {
        const systray = registry.category("systray");
        if (systray.contains("base_tier_validation.ReviewerMenu")) {
            systray.remove("base_tier_validation.ReviewerMenu");
        }
    },
});
