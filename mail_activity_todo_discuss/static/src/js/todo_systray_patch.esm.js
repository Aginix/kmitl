/** @odoo-module **/

import {DiscussTodoView} from "@mail_activity_todo_discuss/js/discuss_todo_view.esm";
import {TodoSystray} from "@mail_activity_todo/js/todo_systray.esm";
import {patch} from "@web/core/utils/patch";

// How many of the newest Todos the systray dropdown lists; the footer links to
// the full Discuss page for the rest.
const SYSTRAY_TODO_LIMIT = 20;

/**
 * With this module installed, the systray lists the Todos themselves (newest
 * first, like the Discuss Todo page) instead of source-app groups, so opening
 * it shows what happened at a glance and one click lands on the source record.
 * "View all" opens the Discuss Todo page. Without this module, the base systray
 * still shows app groups that open the Todo app (correct fallback).
 */
patch(TodoSystray.prototype, "mail_activity_todo_discuss.TodoSystray", {
    setup() {
        this._super(...arguments);
        this.state.todos = [];
    },
    async fetchData() {
        // Base call keeps the badge total; get_my_todos shares its domain.
        await Promise.all([this._super(...arguments), this._fetchTodos()]);
    },
    async _fetchTodos() {
        try {
            const result = await this.orm.call("res.users", "get_my_todos", [false], {
                limit: SYSTRAY_TODO_LIMIT,
            });
            this.state.todos = result.todos || [];
        } catch (error) {
            console.error("Failed to fetch Todos:", error);
            this.state.todos = [];
        }
    },
    // Same row helpers as the Discuss page (neither depends on `this`).
    deadlineInfo: DiscussTodoView.prototype.deadlineInfo,
    createdAgo: DiscussTodoView.prototype.createdAgo,
    onTodoClick(todo) {
        // Open the source record directly, with a pager over the listed Todos
        // of the same model (mirrors DiscussTodoView.onTodoClick).
        if (!todo.res_model || !todo.res_id) {
            return;
        }
        const resIds = [
            ...new Set(
                this.state.todos
                    .filter((t) => t.res_model === todo.res_model && t.res_id)
                    .map((t) => t.res_id)
            ),
        ];
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: todo.res_model,
                res_id: todo.res_id,
                views: [[false, "form"]],
                target: "current",
            },
            {clearBreadcrumbs: true, props: {resIds}}
        );
    },
    _openTodosInDiscuss(resModel = "") {
        // Get() awaits messaging create + init, so discuss is safe to use.
        // Fire-and-forget; swallow a rare init/doAction rejection so it does
        // not surface as an unhandled promise rejection.
        this.env.services.messaging
            .get()
            .then((messaging) => messaging.discuss.openTodos(resModel))
            .catch((error) => console.error("Failed to open Todos in Discuss:", error));
    },
    onViewAllClick() {
        this._openTodosInDiscuss();
    },
});
