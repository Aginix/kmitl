/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";

export class TemplateLineRenderer extends ListRenderer {
    setup() {
        super.setup();
    }
    getActiveColumns(list) {
        const records = list.records || [];
        const budgetType = records[0] ? records[0].data.budget_type : undefined;

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

export class TemplateLine extends X2ManyField {
    setup() {
        super.setup();
    }
}
TemplateLine.components = {
    ...X2ManyField.components,
    ListRenderer: TemplateLineRenderer,
};
registry.category("fields").add("budget_template_line", TemplateLine);
