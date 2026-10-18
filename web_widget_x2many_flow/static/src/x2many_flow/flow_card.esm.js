/** @odoo-module **/

import {Component} from "@odoo/owl";
import {Field} from "@web/views/fields/field";
import {evalDomain} from "@web/views/utils";
import {evaluateExpr} from "@web/core/py_js/py";

/**
 * One Node of the Flow Diagram: a card built from the sub tree's columns — the
 * title column on top, the other card columns below as label/value rows. This is
 * the seam for a future kanban-template card: swap `FlowRenderer.components.FlowCard`.
 */
export class FlowCard extends Component {
    get record() {
        return this.props.record;
    }

    get decorationClasses() {
        return this.props.decorations
            .filter((decoration) =>
                evaluateExpr(decoration.condition, this.record.evalContext)
            )
            .map((decoration) => decoration.class.replace(/^text-/, "o_flow_deco_"));
    }

    get className() {
        const classes = ["o_flow_node", ...this.decorationClasses];
        if (this.props.locked) {
            classes.push("o_flow_locked");
        } else if (this.props.draggable) {
            classes.push("o_flow_draggable");
        }
        return classes.join(" ");
    }

    get titleColumn() {
        const column = this.props.titleColumn;
        return column && this.isShown(column) ? column : null;
    }

    get detailColumns() {
        return this.props.columns.filter(
            (column) => this.isShown(column) && !this.isEmpty(column)
        );
    }

    isShown(column) {
        return !evalDomain(column.modifiers.invisible, this.record.evalContext);
    }

    isEmpty(column) {
        const value = this.record.data[column.name];
        if (value && typeof value === "object" && "count" in value) {
            return value.count === 0;
        }
        return value === false || value === null || value === undefined || value === "";
    }
}
FlowCard.template = "web_widget_x2many_flow.FlowCard";
FlowCard.components = {Field};
FlowCard.props = {
    record: Object,
    archInfo: Object,
    titleColumn: {type: Object, optional: true},
    columns: Array,
    decorations: Array,
    locked: Boolean,
    draggable: Boolean,
    canDelete: Boolean,
    onOpen: Function,
    onDelete: Function,
};
