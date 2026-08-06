/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";
import {formatFloat} from "@web/views/fields/formatters";

/**
 * Editable one2many list that renders the expense lines as a nested tree grouped
 * by ประเภทงบ (project.budget.category), following the category hierarchy up to any
 * depth (in practice three levels). For each category node it injects a sticky
 * header row carrying the roll-up subtotal, and an "add line" row that pre-fills
 * that node's category. The category ancestry is read from two related fields on
 * the line — category_parent_path (ids) and category_complete_name (labels) — so no
 * extra RPC is needed. All standard list editing is reused; only the rows template
 * is extended (see project_budget_table.xml).
 */
export class ProjectBudgetTableRenderer extends ListRenderer {
    /** Ancestor ids of a record's category, root-first, e.g. [3, 7]. Empty when
     * the line has no category yet (a new line before its item is picked). */
    categoryPath(record) {
        const path = record.data.category_parent_path;
        return path
            ? path
                  .split("/")
                  .filter(Boolean)
                  .map(Number)
            : [];
    }

    /** Ancestor chain as [{id, name}, ...], root-first. Zips the id path with the
     * "/"-joined complete name; tolerates a length mismatch by taking the shorter.
     * (Assumes category names contain no " / " — they are curated master data.) */
    categoryChain(record) {
        const ids = this.categoryPath(record);
        const label = record.data.category_complete_name || "";
        const names = label ? label.split(" / ") : [];
        const chain = [];
        const n = Math.min(ids.length, names.length);
        for (let i = 0; i < n; i++) {
            chain.push({id: ids[i], name: names[i]});
        }
        return chain;
    }

    /** Records ordered so every category subtree is contiguous (descendants sit
     * under their ancestors) and category-less lines sink to the bottom. Within the
     * same category, insertion/sequence order is kept. */
    get sortedRecords() {
        return [...this.props.list.records].sort((a, b) => {
            const pa = this.categoryPath(a);
            const pb = this.categoryPath(b);
            if (!pa.length && !pb.length) {
                return 0;
            }
            if (!pa.length) {
                return 1;
            }
            if (!pb.length) {
                return -1;
            }
            const n = Math.min(pa.length, pb.length);
            for (let i = 0; i < n; i++) {
                if (pa[i] !== pb[i]) {
                    return pa[i] - pb[i];
                }
            }
            return pa.length - pb.length;
        });
    }

    /** Roll-up amount per category node: every line adds its amount to each of its
     * ancestors, so a node's total covers its whole subtree. */
    get categoryTotals() {
        const totals = new Map();
        for (const record of this.props.list.records) {
            const amount = record.data.amount || 0;
            for (const id of this.categoryPath(record)) {
                totals.set(id, (totals.get(id) || 0) + amount);
            }
        }
        return totals;
    }

    /** Flat render plan: an ordered list of {type: "header"|"record"|"add"} rows.
     * Headers open when the path diverges going down; add rows close each level as
     * the path shrinks — mirroring the header nesting. */
    get renderRows() {
        const records = this.sortedRecords;
        const totals = this.categoryTotals;
        const rows = [];
        let prev = [];
        records.forEach((record, index) => {
            const chain = this.categoryChain(record);
            let common = 0;
            while (
                common < prev.length &&
                common < chain.length &&
                prev[common].id === chain[common].id
            ) {
                common++;
            }
            for (let level = common; level < chain.length; level++) {
                const node = chain[level];
                rows.push({
                    type: "header",
                    key: `h-${node.id}-${index}`,
                    level,
                    name: node.name,
                    total: totals.get(node.id) || 0,
                });
            }
            rows.push({
                type: "record",
                key: `r-${record.id}`,
                record,
                level: chain.length,
            });
            prev = chain;
            const next = records[index + 1];
            const nextChain = next ? this.categoryChain(next) : [];
            let commonNext = 0;
            while (
                commonNext < chain.length &&
                commonNext < nextChain.length &&
                chain[commonNext].id === nextChain[commonNext].id
            ) {
                commonNext++;
            }
            for (let level = chain.length - 1; level >= commonNext; level--) {
                rows.push({
                    type: "add",
                    key: `a-${chain[level].id}-${index}`,
                    level,
                    categoryId: chain[level].id,
                });
            }
        });
        return rows;
    }

    formatAmount(value) {
        return formatFloat(value, {digits: [16, 2]});
    }

    /** Left padding (rem) for a header/add cell so nesting reads as indentation. */
    indent(level) {
        return `padding-left: ${0.75 + level * 1.5}rem`;
    }

    /** Column count before the amount column, so a header's subtotal cell lines up
     * under จำนวนเงิน (same columns the record rows render). Headers only appear
     * when there is at least one record, so records[0] is always available here. */
    get colsBeforeAmount() {
        const columns = this.getColumns(this.props.list.records[0]);
        const index = columns.findIndex((col) => col.name === "amount");
        return index < 0 ? columns.length : index;
    }

    /** Add a line pre-scoped to a category node, so the new line lands in that
     * section and its item picker is filtered to the node's subtree. */
    addInSection(categoryId) {
        const context = {default_budget_type: "expense"};
        if (categoryId) {
            context.default_category_id = categoryId;
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
