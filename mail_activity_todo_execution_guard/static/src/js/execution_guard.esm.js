/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";
import {attr} from "@mail/model/model_field";
import {session} from "@web/session";

// Execution Todos clear only by acting on the source document: hide the
// manual close buttons (admins keep them to clear stuck Todos).
registerPatch({
    name: "Activity",
    fields: {
        todoCategory: attr(),
        isSourceCleared: attr({
            compute() {
                return this.todoCategory === "execution" && !session.is_system;
            },
        }),
    },
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ("todo_category" in data) {
                data2.todoCategory = data.todo_category;
            }
            return data2;
        },
    },
});

registerPatch({
    name: "ActivityListViewItem",
    fields: {
        hasMarkDoneButton: {
            compute() {
                if (this.activity.isSourceCleared) {
                    return false;
                }
                return this._super();
            },
        },
    },
});
