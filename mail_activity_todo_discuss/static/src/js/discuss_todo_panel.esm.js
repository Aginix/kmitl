/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { useService, useBus } from "@web/core/utils/hooks";

const { useState, onWillStart } = owl;

/**
 * A Todo inbox panel embedded in the Discuss sidebar. It lists the current
 * user's open Todos (capped server-side at 100 via res.users.get_my_todos),
 * so every incoming, actionable item lives alongside the user's chat and
 * mailbox notifications. Clicking a Todo opens its source document; "View all"
 * opens the full Todo app for the remainder.
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
            todos: [],
            totalCount: 0,
            shownCount: 0,
            isOpen: true,
        });

        onWillStart(() => this.fetchData());

        // Live refresh: the server pings "mail_activity_todo/updated" on the
        // user's bus channel; mail_activity_todo's notification handler re-emits
        // it on env.bus as "mail_activity_todo_updated".
        useBus(this.env.bus, "mail_activity_todo_updated", () => this.fetchData());
    }

    async fetchData() {
        try {
            const result = await this.orm.call("res.users", "get_my_todos", []);
            this.state.todos = result.todos || [];
            this.state.totalCount = result.total_count || 0;
            this.state.shownCount = result.shown_count || 0;
        } catch (error) {
            console.error("Failed to fetch Todos:", error);
            this.state.todos = [];
            this.state.totalCount = 0;
            this.state.shownCount = 0;
        }
    }

    toggle() {
        this.state.isOpen = !this.state.isOpen;
    }

    onTodoClick(todo) {
        // Open the Todo's source record. Build the act_window client-side with
        // an explicit `views` (the action service requires it); mail.activity's
        // action_open_document returns only view_mode, which doAction rejects.
        if (!todo.res_model || !todo.res_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: todo.res_model,
            res_id: todo.res_id,
            views: [[false, "form"]],
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
