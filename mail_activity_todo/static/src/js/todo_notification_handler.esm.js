/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Bridge bus.bus -> env.bus: when the server pings "mail_activity_todo/updated"
 * on the current user's channel, re-emit a local "mail_activity_todo_updated"
 * event the systray listens to, so its badge refetches live (no need to open
 * it).
 */
export const todoNotificationHandler = {
    dependencies: ["bus_service"],

    start(env, { bus_service }) {
        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { type } of notifications) {
                if (type === "mail_activity_todo/updated") {
                    env.bus.trigger("mail_activity_todo_updated");
                }
            }
        });
    },
};

registry
    .category("services")
    .add("mail_activity_todo.notification_handler", todoNotificationHandler);
