/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { useService, useBus } from "@web/core/utils/hooks";

const { useState, onWillStart } = owl;

/**
 * A Todo inbox panel embedded in the Discuss sidebar. It reuses the exact
 * server payload the systray uses (res.users.get_my_todo_count), so the count
 * and grouping stay consistent with the systray badge and the Todo app.
 *
 * Rationale: every incoming thing addressed to the user — chat, mailbox
 * notifications and actionable Todos — should be reachable from one place.
 *
 * Registered as a messaging component so it can be referenced from the
 * inherited mail.DiscussSidebar template (legacy mail framework, Odoo 16.0).
 */
export class DiscussTodoPanel extends LegacyComponent {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            groups: [],
            totalCount: 0,
            isOpen: true,
        });
        this.treeViewId = false;
        this.formViewId = false;

        onWillStart(() => this.fetchData());

        // Live refresh: the server pings "mail_activity_todo/updated" on the
        // user's bus channel; mail_activity_todo's notification handler re-emits
        // it on env.bus as "mail_activity_todo_updated".
        useBus(this.env.bus, "mail_activity_todo_updated", () => this.fetchData());
    }

    async fetchData() {
        try {
            const result = await this.orm.call("res.users", "get_my_todo_count", []);
            this.state.groups = result.groups || [];
            this.state.totalCount = result.total_count || 0;
            this.treeViewId = result.tree_view_id || false;
            this.formViewId = result.form_view_id || false;
        } catch (error) {
            console.error("Failed to fetch Todo count:", error);
            this.state.groups = [];
            this.state.totalCount = 0;
        }
    }

    toggle() {
        this.state.isOpen = !this.state.isOpen;
    }

    onGroupClick(group) {
        // Drill into the Todo inbox filtered to this source model.
        this.action.doAction({
            type: "ir.actions.act_window",
            name: group.name,
            res_model: "mail.activity",
            domain: [
                ["is_my_todo", "=", true],
                ["is_read_by_me", "=", false],
                ["res_model_id", "=", group.model_id],
            ],
            views: [
                [this.treeViewId, "list"],
                [this.formViewId, "form"],
            ],
            target: "current",
        });
    }

    onViewAllClick() {
        this.action.doAction("mail_activity_todo.action_my_todos");
    }
}

Object.assign(DiscussTodoPanel, {
    props: {},
    template: "mail_activity_todo_discuss.DiscussTodoPanel",
});

registerMessagingComponent(DiscussTodoPanel);
