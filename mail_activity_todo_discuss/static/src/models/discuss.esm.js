/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";
import { attr } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";

/**
 * Make "Todos" a first-class destination in the Discuss main content pane,
 * alongside the Inbox/Starred/History mailboxes. The flag lives on the Discuss
 * singleton so the sidebar row, the content pane and the systray all share one
 * source of truth.
 */
registerPatch({
    name: "Discuss",
    fields: {
        // When true, the main content pane shows the Todo inbox instead of a
        // conversation. Mutually exclusive with an active thread.
        isTodoActive: attr({ default: false }),
    },
    recordMethods: {
        /**
         * Show the Todo inbox in the Discuss main pane (opening Discuss first if
         * needed). Mirrors openThread(): clear the active thread so the
         * conversation pane hides, then flag the Todo view on.
         *
         * Presets isInitThreadHandled so DiscussContainer's one-time
         * "open Inbox on first Discuss open" does not steal focus when the
         * systray routes the user straight to Todos.
         */
        openTodos() {
            this.update({
                thread: clear(),
                isTodoActive: true,
                isInitThreadHandled: true,
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
