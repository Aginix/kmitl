/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Bridge bus.bus -> env.bus: relay "mail_workflow_notification/updated"
 * from the server channel into a local event the systray listens to.
 */
export const workflowNotificationHandler = {
    dependencies: ["bus_service"],

    start(env, { bus_service }) {
        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { type } of notifications) {
                if (type === "mail_workflow_notification/updated") {
                    env.bus.trigger("workflow_notification_updated");
                }
            }
        });
    },
};

registry
    .category("services")
    .add(
        "mail_workflow_notification.notification_handler",
        workflowNotificationHandler
    );
