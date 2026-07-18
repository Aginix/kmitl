/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";

/**
 * Editable one2many list that renders a bold ประเภทงบ section header row each
 * time the budget category changes. Records are ordered by budget_category_id
 * server-side, so consecutive rows of the same category cluster together and a
 * header is injected at each boundary. All standard list editing is reused —
 * only the rows template is extended (see project_budget_table.xml).
 */
export class ProjectBudgetTableRenderer extends ListRenderer {
    /** True when this record opens a new section (or is the first row). */
    startsSection(record) {
        const records = this.props.list.records;
        const index = records.indexOf(record);
        if (index <= 0) {
            return true;
        }
        return this.categoryKey(records[index - 1]) !== this.categoryKey(record);
    }

    /** True when this record is the last of its section (or the last row). */
    endsSection(record) {
        const records = this.props.list.records;
        const index = records.indexOf(record);
        if (index === records.length - 1) {
            return true;
        }
        return this.categoryKey(records[index + 1]) !== this.categoryKey(record);
    }

    categoryKey(record) {
        const cat = record.data.budget_category_id;
        return cat ? cat[0] : false;
    }

    sectionName(record) {
        const cat = record.data.budget_category_id;
        return cat && cat[1] ? cat[1] : "ไม่ระบุประเภทงบ";
    }

    /** Add a line pre-scoped to this record's section (category), so the new
     * line lands in the section and its item picker is filtered to it. */
    addInSection(record) {
        const context = {default_budget_type: "expense"};
        const categoryId = this.categoryKey(record);
        if (categoryId) {
            context.default_budget_category_id = categoryId;
        }
        this.add({context});
    }
}
ProjectBudgetTableRenderer.rowsTemplate = "kmitl_project.ProjectBudgetTableRows";

export class ProjectBudgetTable extends X2ManyField {}
ProjectBudgetTable.components = {
    ...X2ManyField.components,
    ListRenderer: ProjectBudgetTableRenderer,
};

registry.category("fields").add("project_budget_table", ProjectBudgetTable);
