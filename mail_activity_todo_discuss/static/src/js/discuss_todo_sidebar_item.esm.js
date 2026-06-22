/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { useService, useBus } from "@web/core/utils/hooks";

const { useState, onWillStart } = owl;

/**
 * A "Todos" row in the Discuss sidebar, mirroring the Inbox/Starred/History
 * mailbox rows. Clicking it shows the Todo inbox in the main pane
 * (discuss.openTodos); its active state and unread count track the shared
 * Discuss flag and a live count fetched from res.users.get_my_todo_total.
 */
export class DiscussTodoSidebarItem extends LegacyComponent {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({ count: 0 });

        onWillStart(() => this.fetchCount());
        useBus(this.env.bus, "mail_activity_todo_updated", () => this.fetchCount());
    }

    get discussView() {
        return this.props.record;
    }

    async fetchCount() {
        try {
            // Just the badge number (single search_count) — no per-app grouping.
            const result = await this.orm.call("res.users", "get_my_todo_total", []);
            this.state.count = result.total_count || 0;
        } catch (error) {
            this.state.count = 0;
        }
    }

    onClick() {
        this.discussView.discuss.openTodos();
    }
}

Object.assign(DiscussTodoSidebarItem, {
    props: { record: Object },
    template: "mail_activity_todo_discuss.DiscussTodoSidebarItem",
});

registerMessagingComponent(DiscussTodoSidebarItem);
