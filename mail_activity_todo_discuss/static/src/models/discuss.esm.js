/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";
import { attr } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";

/**
 * Make "Todos" a first-class destination in the Discuss main content pane,
 * alongside the Inbox/Starred/History mailboxes. The flags live on the Discuss
 * singleton so the sidebar panel, the content pane and the systray all share
 * one source of truth.
 */
registerPatch({
    name: "Discuss",
    fields: {
        // When true, the main content pane shows the Todo inbox instead of a
        // conversation. Mutually exclusive with an active thread.
        isTodoActive: attr({ default: false }),
        // When true, the Todo pane shows the History (read/dismissed Todos)
        // instead of the open inbox. Only meaningful while isTodoActive.
        isTodoHistory: attr({ default: false }),
        // Optional source-model filter (e.g. "purchase.order") set when a
        // sidebar app group is clicked; empty string means "all apps".
        todoResModel: attr({ default: "" }),
    },
    recordMethods: {
        /**
         * Show the Todo inbox in the Discuss main pane, optionally filtered to
         * one source app. "" = all apps.
         *
         * @param {string} [resModel=""] source model to filter to, "" = all
         */
        openTodos(resModel = "") {
            this._showTodoPane({
                isTodoHistory: false,
                todoResModel: resModel || "",
            });
        },
        /**
         * Show the Todo History (my read/dismissed Todos, all apps) in the
         * Discuss main pane.
         */
        openTodoHistory() {
            this._showTodoPane({ isTodoHistory: true, todoResModel: "" });
        },
        /**
         * Reveal the Todo pane in the Discuss main pane (opening Discuss first
         * if needed). Mirrors openThread(): clear the active thread so the
         * conversation pane hides, then flag the Todo view on.
         *
         * Presets isInitThreadHandled so DiscussContainer's one-time
         * "open Inbox on first Discuss open" does not steal focus when the
         * systray routes the user straight to Todos.
         *
         * @param {Object} extra fields to set (isTodoHistory / todoResModel)
         */
        _showTodoPane(extra) {
            this.update({
                thread: clear(),
                isTodoActive: true,
                isInitThreadHandled: true,
                ...extra,
            });
            if (!this.discussView) {
                this.env.services.action.doAction("mail.action_discuss", {
                    name: this.env._t("Todos"),
                    clearBreadcrumbs: false,
                });
            }
        },
        /**
         * Leave the Todo view the moment a real thread (mailbox/channel) is
         * selected, so the two are never highlighted at once.
         */
        _onChangeThreadResetTodo() {
            if (this.thread && this.isTodoActive) {
                this.update({ isTodoActive: false });
            }
        },
    },
    onChanges: [
        // "thread" is the base mail Discuss field (the selected mailbox/channel).
        { dependencies: ["thread"], methodName: "_onChangeThreadResetTodo" },
    ],
});
