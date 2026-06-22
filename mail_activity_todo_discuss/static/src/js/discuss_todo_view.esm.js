/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { useService, useBus } from "@web/core/utils/hooks";

const { useState, onWillStart } = owl;

/**
 * The Todo inbox rendered in the Discuss MAIN content pane (when
 * discuss.isTodoActive). Lists the current user's open Todos (capped at 100 by
 * res.users.get_my_todos); clicking one opens its source document, and the
 * footer/header links open the full Todo app for the remainder.
 *
 * Registered as a messaging component so the patched mail.Discuss.content
 * template can reference <DiscussTodoView/> with no import.
 */
export class DiscussTodoView extends LegacyComponent {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ todos: [], totalCount: 0 });

        onWillStart(() => this.fetchData());
        useBus(this.env.bus, "mail_activity_todo_updated", () => this.fetchData());
    }

    get discussView() {
        return this.props.record;
    }

    async fetchData() {
        try {
            const result = await this.orm.call("res.users", "get_my_todos", []);
            this.state.todos = result.todos || [];
            this.state.totalCount = result.total_count || 0;
        } catch (error) {
            console.error("Failed to fetch Todos:", error);
            this.state.todos = [];
            this.state.totalCount = 0;
        }
    }

    onTodoClick(todo) {
        // Open the Todo's source record. Build the act_window client-side with
        // an explicit `views` (the action service requires it).
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

Object.assign(DiscussTodoView, {
    props: { record: Object },
    template: "mail_activity_todo_discuss.DiscussTodoView",
});

registerMessagingComponent(DiscussTodoView);
