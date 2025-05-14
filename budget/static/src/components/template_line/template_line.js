/** @odoo-module **/

import {registry} from "@web/core/registry";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {ListRenderer} from "@web/views/list/list_renderer";

export class Template_line_renderer extends ListRenderer {
    setup() {
        super.setup();
    }
    getActiveColumns(list) {
        const budgetType = list?.records?.[0]?.data?.budget_type;

        return this.allColumns.filter((col) => {
            if (list.isGrouped && col.widget === "handle") {
                return false;
            }
            if (budgetType !== "expense" && col.name === "budgetable") {
                return false;
            }

            return !col.optional || this.optionalActiveFields[col.name];
        });
    }
}

export class Template_line extends X2ManyField {
    setup() {
        super.setup();
    }
}
Template_line.template = "budget.Template_line";
Template_line.components = {
    ...X2ManyField.components,
    ListRenderer: Template_line_renderer,
};
registry.category("fields").add("template_line", Template_line);
