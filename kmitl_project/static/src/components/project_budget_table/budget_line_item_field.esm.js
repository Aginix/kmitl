/** @odoo-module **/

import {registry} from "@web/core/registry";
import {Field} from "@web/views/fields/field";
import {CharField} from "@web/views/fields/char/char_field";

const {Component} = owl;

/**
 * Polymorphic "รายการ" cell for the Project Budget Plan expense table — it collapses
 * the former "เลือกจากรายการ" (budget_item_id) and "รายการ" (name) columns into one.
 * Per row it follows is_custom, for both the read-only value and the inline editor:
 *   - catalog line (is_custom = false) → render the budget_item_id many2one picker
 *   - custom line  (is_custom = true)  → render the free-text name char
 *
 * The widget is bound to the `name` field, so the custom case is rendered with a
 * plain CharField (rendering it through <Field> would recurse into this widget). The
 * catalog case is rendered through <Field name="budget_item_id">, whose fieldInfo is
 * read from record.activeFields — so budget_item_id must be present (invisible) in
 * the tree arch to carry its domain/options.
 */
export class BudgetLineItemField extends Component {
    get isCustom() {
        return Boolean(this.props.record.data.is_custom);
    }

    /** Show the budget_item_id picker only for a catalog line that is being edited.
     * A catalog line that is not in edition (and every custom line) renders the leaf
     * name instead, so the readonly value stays the compact name even right after an
     * item is picked (the picker's dropdown label is the full path). */
    get showItemPicker() {
        return !this.isCustom && this.props.record.isInEdition;
    }

    get itemFieldInfo() {
        // Render the sibling picker even though its arch node is invisible: strip the
        // (column_)invisible modifiers so this manual <Field/> is not suppressed.
        const info = this.props.record.activeFields.budget_item_id;
        return {
            ...info,
            modifiers: {
                ...(info.modifiers || {}),
                invisible: false,
                column_invisible: false,
            },
        };
    }
}
BudgetLineItemField.template = "kmitl_project.BudgetLineItemField";
BudgetLineItemField.components = {Field, CharField};

registry.category("fields").add("budget_line_item", BudgetLineItemField);
