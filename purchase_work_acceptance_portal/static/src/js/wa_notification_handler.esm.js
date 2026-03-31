/** @odoo-module **/

import { registry } from "@web/core/registry";

export const waNotificationHandler = {
    dependencies: ["bus_service", "multi_tab"],

    start(env, { bus_service, multi_tab }) {
        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type === "work_acceptance/inbox") {
                    env.bus.trigger("wa_inbox_updated", payload);
                }
            }
        });
    },
};

registry.category("services").add("waNotificationHandler", waNotificationHandler);
