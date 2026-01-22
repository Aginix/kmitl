/** @odoo-module **/

import { registry } from "@web/core/registry";

export const sarabunNotificationHandler = {
    dependencies: ["bus_service", "action"],

    start(env, { bus_service, action }) {
        bus_service.subscribe("sarabun_inbox/updated", (payload) => {
            // Trigger custom event that systray can listen to
            env.bus.trigger("sarabun_inbox_updated", payload);
        });
    },
};

registry.category("services").add("sarabunNotificationHandler", sarabunNotificationHandler);
