/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TodoSystray } from "@mail_activity_todo/js/todo_systray.esm";

/**
 * With this module installed, the Discuss Todo page exists — so route every
 * systray click there instead of to the backend list, keeping all incoming
 * work in one place. Without this module, the base systray still opens the
 * Todo app (correct fallback).
 */
patch(TodoSystray.prototype, "mail_activity_todo_discuss.TodoSystray", {
    _openTodosInDiscuss() {
        // get() awaits messaging create + init, so discuss is safe to use.
        // Fire-and-forget; swallow a rare init/doAction rejection so it does
        // not surface as an unhandled promise rejection.
        this.env.services.messaging
            .get()
            .then((messaging) => messaging.discuss.openTodos())
            .catch((error) =>
                console.error("Failed to open Todos in Discuss:", error)
            );
    },
    // Route every systray click to the single Todos page in Discuss. The base
    // per-source-app drill-down (the `group` arg) is intentionally collapsed
    // into the unified pane; the signature is kept for clarity.
    onGroupClick(group) {
        this._openTodosInDiscuss();
    },
    onViewAllClick() {
        this._openTodosInDiscuss();
    },
});
