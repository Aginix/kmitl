/** @odoo-module **/

import { registry } from "@web/core/registry";

export const sarabunNotificationHandler = {
    dependencies: ["bus_service"],

    start(env, { bus_service }) {
        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type === "sarabun_inbox/updated") {
                    env.bus.trigger("sarabun_inbox_updated", payload);
                }
            }
        });
    },
};

registry.category("services").add("sarabunNotificationHandler", sarabunNotificationHandler);
