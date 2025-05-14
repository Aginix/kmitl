/** @odoo-module **/

import {registry} from "@web/core/registry";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {ListRenderer} from "@web/views/list/list_renderer";

export class TemplateLineRenderer extends ListRenderer {
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
