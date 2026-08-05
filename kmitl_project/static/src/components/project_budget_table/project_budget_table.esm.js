/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";
import {formatFloat} from "@web/views/fields/formatters";

/**
 * Editable one2many list that renders a bold ประเภทงบ section header row each
 * time the budget category changes. Records are ordered by budget_category_id
 * server-side, so consecutive rows of the same category cluster together and a
 * header is injected at each boundary. All standard list editing is reused —
 * only the rows template is extended (see project_budget_table.xml).
 */
export class ProjectBudgetTableRenderer extends ListRenderer {
    /** Records grouped by budget category so a freshly added line shows inside
     * its section instead of at the end of the list. Category-less rows (a new
     * line before its item is picked) sort to the bottom; stable within a
     * category so sequence/insertion order is kept. */
    get sortedRecords() {
        return [...this.props.list.records].sort((a, b) => {
            const ka = this.categoryKey(a);
            const kb = this.categoryKey(b);
            if (ka === kb) {
                return 0;
            }
            if (!ka) {
                return 1;
            }
            if (!kb) {
                return -1;
            }
            return ka - kb;
        });
    }

    /** True when this record opens a new section (or is the first row). */
    startsSection(record, index) {
        if (index <= 0) {
            return true;
        }
        return (
            this.categoryKey(this.sortedRecords[index - 1]) !==
            this.categoryKey(record)
        );
    }

    /** True when this record is the last of its section (or the last row). */
    endsSection(record, index) {
        const records = this.sortedRecords;
        if (index >= records.length - 1) {
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

    /** Sum of the amount of every line in this record's section. */
    sectionTotal(record) {
        const key = this.categoryKey(record);
        let total = 0;
        for (const rec of this.props.list.records) {
            if (this.categoryKey(rec) === key) {
                total += rec.data.amount || 0;
            }
        }
        return total;
    }

    formatAmount(value) {
        return formatFloat(value, {digits: [16, 2]});
    }

    /** Column count before the amount column, so the subtotal cell lines up
     * under จำนวนเงิน (same columns the record rows render). */
    colsBeforeAmount(record) {
        const columns = this.getColumns(record);
        const index = columns.findIndex((col) => col.name === "amount");
        return index < 0 ? columns.length : index;
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
