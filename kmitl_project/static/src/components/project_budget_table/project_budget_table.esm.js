/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";
import {formatFloat} from "@web/views/fields/formatters";
import {useService} from "@web/core/utils/hooks";

const {onWillStart} = owl;

/**
 * Editable one2many list that renders the expense lines as a nested tree grouped
 * by ประเภทงบ (project.budget.category), following the category hierarchy up to any
 * depth (in practice three levels). For each category node it injects a sticky
 * header row carrying the roll-up subtotal, and an "add line" row that pre-fills
 * that node's category. Every active category is rendered (one RPC on start), so a
 * section's add buttons exist before it holds any line. A line's ancestry is read
 * from two related fields — category_parent_path (ids) and category_complete_name
 * (labels). All standard list editing is reused; only the rows template
 * is extended (see project_budget_table.xml).
 */
export class ProjectBudgetTableRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        // Every active ประเภทงบ, so each one renders as a section — with its add
        // buttons — even before it holds any line.
        onWillStart(async () => {
            this.categories = await this.orm.searchRead(
                "project.budget.category",
                [],
                ["complete_name", "parent_path"]
            );
        });
    }

    /** Ancestor chain as [{id, name}, ...], root-first, from a category's
     * materialised id path (e.g. "3/7/") and "/"-joined complete name. Tolerates a
     * length mismatch by taking the shorter. (Assumes category names contain no
     * " / " — they are curated master data.) */
    chainOf(path, label) {
        const ids = path ? path.split("/").filter(Boolean).map(Number) : [];
        const names = label ? label.split(" / ") : [];
        const chain = [];
        const n = Math.min(ids.length, names.length);
        for (let i = 0; i < n; i++) {
            chain.push({id: ids[i], name: names[i]});
        }
        return chain;
    }

    /** A record's category chain. Empty when the line has no category yet (a new
     * line before its item is picked). */
    categoryChain(record) {
        return this.chainOf(
            record.data.category_parent_path,
            record.data.category_complete_name
        );
    }

    /** Roll-up amount per category node: every line adds its amount to each of its
     * ancestors, so a node's total covers its whole subtree. */
    get categoryTotals() {
        const totals = new Map();
        for (const record of this.props.list.records) {
            const amount = record.data.amount || 0;
            for (const {id} of this.categoryChain(record)) {
                totals.set(id, (totals.get(id) || 0) + amount);
            }
        }
        return totals;
    }

    /** Flat render plan: an ordered list of {type: "header"|"record"|"add"} rows,
     * walking the ประเภทงบ tree depth-first — each node's header, then its own
     * lines, then its sub-sections, then its add row. When lines can be added,
     * every active category is a node (so empty sections still offer their add
     * buttons); otherwise only the categories holding lines are. Category-less
     * lines sink to the bottom. */
    get renderRows() {
        const totals = this.categoryTotals;
        const nodes = new Map();
        const addChain = (chain) => {
            chain.forEach((node, level) => {
                if (!nodes.has(node.id)) {
                    nodes.set(node.id, {
                        ...node,
                        level,
                        parentId: level ? chain[level - 1].id : null,
                        children: [],
                        records: [],
                    });
                }
            });
        };
        if (this.displayRowCreates) {
            for (const cat of this.categories) {
                addChain(this.chainOf(cat.parent_path, cat.complete_name));
            }
        }
        const loose = [];
        for (const record of this.props.list.records) {
            const chain = this.categoryChain(record);
            if (chain.length) {
                addChain(chain);
                nodes.get(chain[chain.length - 1].id).records.push(record);
            } else {
                loose.push(record);
            }
        }
        const roots = [];
        for (const node of nodes.values()) {
            (node.parentId ? nodes.get(node.parentId).children : roots).push(node);
        }
        const byId = (a, b) => a.id - b.id;
        const rows = [];
        const visit = (node) => {
            rows.push({
                type: "header",
                key: `h-${node.id}`,
                level: node.level,
                name: node.name,
                total: totals.get(node.id) || 0,
            });
            for (const record of node.records) {
                rows.push({type: "record", key: `r-${record.id}`, record});
            }
            node.children.sort(byId).forEach(visit);
            rows.push({
                type: "add",
                key: `a-${node.id}`,
                level: node.level,
                categoryId: node.id,
            });
        };
        roots.sort(byId).forEach(visit);
        for (const record of loose) {
            rows.push({type: "record", key: `r-${record.id}`, record});
        }
        return rows;
    }

    /** No blank filler rows under the always-present sections. */
    get getEmptyRowIds() {
        return this.displayRowCreates && this.categories.length
            ? []
            : super.getEmptyRowIds;
    }

    formatAmount(value) {
        return formatFloat(value, {digits: [16, 2]});
    }

    /** Left padding (rem) for a header/add cell so nesting reads as indentation. */
    indent(level) {
        return `padding-left: ${0.75 + level * 1.5}rem`;
    }

    /** Column count before the amount column, so a header's subtotal cell lines up
     * under จำนวนเงิน (same columns the record rows render). */
    get colsBeforeAmount() {
        const columns = this.getColumns(this.props.list.records[0]);
        const index = columns.findIndex((col) => col.name === "amount");
        return index < 0 ? columns.length : index;
    }

    /** Add a line pre-scoped to a category node, so the new line lands in that
     * section (its ประเภทงบ pre-filled and hidden) and its item picker is filtered to
     * the node's subtree. ``isCustom`` marks a free-text line ("เพิ่มอื่น ๆ"): the
     * catalog picker is hidden and only รายการ / คำอธิบาย / จำนวนเงิน are shown. */
    addInSection(categoryId, isCustom) {
        const context = {
            default_budget_type: "expense",
            default_is_custom: Boolean(isCustom),
        };
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
