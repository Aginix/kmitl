/** @odoo-module **/

import {buildLayers, resolveLayerKey} from "./layer_utils.esm";
import {onWillStart, useState} from "@odoo/owl";
import {FlowRenderer} from "./flow_renderer.esm";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {_lt} from "@web/core/l10n/translation";
import {browser} from "@web/core/browser/browser";
import {registry} from "@web/core/registry";
import {sprintf} from "@web/core/utils/strings";

const DIRECTIONS = ["vertical", "horizontal"];

/**
 * `x2many_flow`: a one2many drawn as a Flow Diagram instead of a table. Lines are
 * stacked in Layers by a numeric Layer Key; lines sharing a value sit side by side
 * in one Layer. Cards come from the sub tree's columns; create / edit go through
 * the standard x2many dialog (the sub form), so everything X2ManyField already does
 * — context, domain, access rights, Save & New — is reused as is.
 *
 *     <field name="line_ids" widget="x2many_flow"
 *            options="{'order_field': 'sequence', 'direction': 'horizontal',
 *                      'title_field': 'name', 'card_fields': ['user_id', 'state']}">
 *         <tree>...</tree>
 *         <form>...</form>
 *     </field>
 *
 * See CONTEXT.md for the vocabulary and docs/adr/ for the reorder rule.
 */
export class X2ManyFlowField extends X2ManyField {
    setup() {
        super.setup();
        this.archInfo =
            (this.viewMode === "list" && this.activeField.views.list) || null;
        this.layerKey = this.archInfo
            ? resolveLayerKey(this.archInfo, this.list.fields, this.props.orderField)
            : {error: "no_tree"};

        this.storageKey = `x2many_flow:${this.props.record.resModel}:${this.props.name}`;
        const stored = browser.localStorage.getItem(this.storageKey);
        this.flowState = useState({
            direction: DIRECTIONS.includes(stored) ? stored : this.props.direction,
        });

        // The diagram has no pager: show every line.
        onWillStart(async () => {
            if (!this.layerKey.error && this.list.count > this.list.limit) {
                await this.list.load({limit: this.list.count, offset: 0});
            }
        });
    }

    get errorMessage() {
        const {error, name} = this.layerKey;
        const messages = {
            no_tree: this.env._t("The flow diagram needs a <tree> inside the field."),
            no_field: this.env._t("No Layer Key field found (%s)."),
            not_numeric: this.env._t(
                "The Layer Key field %s must be an Integer or a Float."
            ),
            not_in_tree: this.env._t(
                "The Layer Key field %s must be a column of the <tree>."
            ),
        };
        return error && sprintf(messages[error], name);
    }

    /** Field columns not column_invisible, the same filter X2ManyField applies. */
    get visibleColumns() {
        return this.archInfo.columns.filter(
            (column) =>
                column.type === "field" &&
                column.name !== this.layerKey.name &&
                !this.evalColumnInvisibleModifier(column.modifiers)
        );
    }

    get titleColumn() {
        const columns = this.visibleColumns;
        const {titleField} = this.props;
        return (
            (titleField && columns.find((column) => column.name === titleField)) ||
            columns.find((column) => column.optional !== "hide")
        );
    }

    get cardColumns() {
        const columns = this.visibleColumns;
        const title = this.titleColumn;
        if (this.props.cardFields) {
            return this.props.cardFields
                .map((name) => columns.find((column) => column.name === name))
                .filter((column) => column && column !== title);
        }
        return columns.filter(
            (column) => column !== title && column.optional !== "hide"
        );
    }

    get direction() {
        return this.env.isSmall ? "vertical" : this.flowState.direction;
    }

    get flowRendererProps() {
        const readonly = Boolean(this.props.readonly);
        return {
            list: this.list,
            archInfo: this.archInfo,
            layerKey: this.layerKey.name,
            titleColumn: this.titleColumn,
            columns: this.cardColumns,
            direction: this.direction,
            cardWidth: this.props.cardWidth,
            canToggleDirection: !this.env.isSmall,
            readonly,
            canCreate: !readonly && Boolean(this.activeActions.create),
            canDelete: !readonly && Boolean(this.activeActions.onDelete),
            onAdd: (value) => this.onAddInLayer(value),
            onOpen: (record) => this.openRecord(record),
            onDelete: (record) => this.activeActions.onDelete(record),
            onToggleDirection: () => this.toggleDirection(),
            applyUpdates: (updates) => this.applyLayerUpdates(updates),
        };
    }

    /**
     * Open the create dialog pre-filled with a Layer Key: the given Layer's
     * value, or a New Layer after the last one.
     *
     * @param {Number|null} value Layer value, null for a New Layer
     * @returns {Promise}
     */
    onAddInLayer(value) {
        let layerValue = value;
        if (layerValue === null) {
            const layers = buildLayers(this.list.records, this.layerKey.name);
            layerValue = layers.length ? layers[layers.length - 1].value + 1 : 1;
        }
        return this.onAdd({
            context: {[`default_${this.layerKey.name}`]: layerValue},
            editable: false,
        });
    }

    toggleDirection() {
        const direction =
            this.flowState.direction === "vertical" ? "horizontal" : "vertical";
        this.flowState.direction = direction;
        browser.localStorage.setItem(this.storageKey, direction);
    }

    /**
     * Write every Layer Key change of one drop in a single notification — not
     * StaticList.resequence, which renumbers consecutively and would merge or
     * split Layers.
     *
     * @param {Array<{record: Object, value: Number}>} updates from planDrop
     * @returns {Promise}
     */
    applyLayerUpdates(updates) {
        return this.list.applyCommands(
            this.props.name,
            updates.map(({record, value}) => ({
                operation: "UPDATE",
                record,
                data: {[this.layerKey.name]: value},
            }))
        );
    }
}
X2ManyFlowField.template = "web_widget_x2many_flow.X2ManyFlowField";
X2ManyFlowField.components = {...X2ManyField.components, FlowRenderer};
// Resolved on access, not copied: modules loaded after this one (e.g.
// web_m2x_options adds `open`) still extend X2ManyField.props/extractProps, and
// extractProps below forwards their keys — a snapshot would fail props validation.
Object.defineProperty(X2ManyFlowField, "props", {
    get: () => ({
        ...X2ManyField.props,
        orderField: {type: String, optional: true},
        direction: {type: String, optional: true},
        titleField: {type: String, optional: true},
        cardFields: {type: Array, element: String, optional: true},
        cardWidth: {type: String, optional: true},
    }),
});
X2ManyFlowField.defaultProps = {direction: "vertical"};
X2ManyFlowField.supportedTypes = ["one2many"];
X2ManyFlowField.displayName = _lt("Flow Diagram");
X2ManyFlowField.extractProps = (params) => {
    const {options} = params.attrs;
    return {
        ...X2ManyField.extractProps(params),
        orderField: options.order_field,
        direction: DIRECTIONS.includes(options.direction)
            ? options.direction
            : undefined,
        titleField: options.title_field,
        cardFields: options.card_fields,
        // A bare number is pixels; a string is any CSS length ("22rem").
        cardWidth:
            typeof options.card_width === "number"
                ? `${options.card_width}px`
                : options.card_width,
    };
};

registry.category("fields").add("x2many_flow", X2ManyFlowField);
