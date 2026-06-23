/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { useService, useBus } from "@web/core/utils/hooks";

const { useState, useEffect } = owl;

const CATEGORY_LABELS = {
    approval: "Approval",
    execution: "Execution",
    acknowledgement: "Acknowledgement",
    fyi: "FYI",
};

/**
 * The Todo inbox rendered in the Discuss MAIN content pane (when
 * discuss.isTodoActive). Lists the current user's open Todos with their detail
 * fields (capped at 100 by res.users.get_my_todos), optionally filtered to one
 * source app via discuss.todoResModel (set by the sidebar groups). Clicking a
 * Todo opens its source document; the header/footer link opens the full Todo
 * app for the remainder.
 *
 * Registered as a messaging component so the patched mail.Discuss.content
 * template can reference <DiscussTodoView/> with no import.
 */
export class DiscussTodoView extends LegacyComponent {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ todos: [], totalCount: 0, loaded: false });

        // Fetch on mount and whenever the source-app filter changes (the deps
        // read discuss.todoResModel, which the template also reads, so useModels
        // re-renders and this effect re-runs on a sidebar group click).
        useEffect(
            () => {
                this.fetchData();
            },
            () => [this.discuss.todoResModel]
        );
        useBus(this.env.bus, "mail_activity_todo_updated", () => this.fetchData());
    }

    get discuss() {
        return this.props.record.discuss;
    }

    get filterLabel() {
        // Load-bearing: this read of discuss.todoResModel (evaluated every render
        // via the header's t-if="filterLabel") is what subscribes useModels to
        // the field, so openTodos(resModel) re-renders and the useEffect refetch
        // fires. Keep reading todoResModel here unconditionally.
        if (!this.discuss.todoResModel) {
            return "";
        }
        return this.state.todos.length
            ? this.state.todos[0].app
            : this.discuss.todoResModel;
    }

    categoryLabel(code) {
        return CATEGORY_LABELS[code] || "";
    }

    async fetchData() {
        try {
            const resModel = this.discuss.todoResModel || false;
            const result = await this.orm.call("res.users", "get_my_todos", [
                resModel,
            ]);
            this.state.todos = result.todos || [];
            this.state.totalCount = result.total_count || 0;
        } catch (error) {
            console.error("Failed to fetch Todos:", error);
            this.state.todos = [];
            this.state.totalCount = 0;
        } finally {
            // Latches true after the first fetch so the empty-state never
            // flashes before data arrives (and refetches keep the current list
            // visible rather than blanking).
            this.state.loaded = true;
        }
    }

    onShowAll() {
        // Stay on the Todo page, drop the per-app filter.
        this.discuss.openTodos();
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
