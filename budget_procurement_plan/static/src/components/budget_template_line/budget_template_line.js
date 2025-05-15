/** @odoo-module **/
import {registry} from "@web/core/registry";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {TemplateLineRenderer} from "@budget/components/template_line/template_line";

export class CustomTemplateLineRenderer extends TemplateLineRenderer {
    setup() {
        super.setup();
    }
    getActiveColumns(list) {
        const budgetType = list?.records?.[0]?.data?.budget_type;
        const columns = super.getActiveColumns(list)
        return columns.filter((col) => {
        	if (budgetType === 'revenue' && col.name === 'procurement_plan') {
        		return false
        	}

        	return true
        })
    }
}
export class CustomTemplateLine extends X2ManyField {
    setup() {
        super.setup();
    }
}
CustomTemplateLine.components = {
    ...X2ManyField.components,
    ListRenderer: CustomTemplateLineRenderer,
};
registry.category("fields").add("budget_template_line_custom", CustomTemplateLine);
