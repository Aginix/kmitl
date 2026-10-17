/** @odoo-module **/

import {Component, useRef} from "@odoo/owl";
import {buildLayers, planDrop} from "./layer_utils.esm";
import {FlowCard} from "./flow_card.esm";
import {sprintf} from "@web/core/utils/strings";
import {useService} from "@web/core/utils/hooks";
import {useSortable} from "@web/core/utils/sortable";

/**
 * Lays the Nodes out as Layers (rows sharing one Layer Key value) joined by
 * fork/join connectors, with a drop zone ("gap") before, between and after the
 * Layers. Dropping a Node on a Layer joins it; dropping it in a gap makes a New
 * Layer (planDrop). Layers and gaps share the `.o_flow_drop` group class because
 * useSortable prefixes its element selector with the group selector.
 */
export class FlowRenderer extends Component {
    setup() {
        this.notification = useService("notification");
        this.rootRef = useRef("root");
        // Drag feedback is toggled on the DOM, not rendered: the hook's state is
        // not component-reactive, and re-rendering mid-drag would disturb the
        // ghost element the hook inserted.
        useSortable({
            enable: () => !this.props.readonly,
            ref: this.rootRef,
            groups: ".o_flow_drop",
            connectGroups: true,
            elements: ".o_flow_node:not(.o_flow_locked)",
            handle: ".o_flow_handle",
            cursor: "grabbing",
            onDragStart: () => this.rootRef.el.classList.add("o_flow_dragging"),
            onGroupEnter: ({group}) => group.classList.add("o_flow_drop_hover"),
            onGroupLeave: ({group}) => group.classList.remove("o_flow_drop_hover"),
            onDragEnd: () => {
                this.rootRef.el.classList.remove("o_flow_dragging");
                for (const el of this.rootRef.el.querySelectorAll(
                    ".o_flow_drop_hover"
                )) {
                    el.classList.remove("o_flow_drop_hover");
                }
            },
            onDrop: (params) => this.onDrop(params),
        });
    }

    get layers() {
        return buildLayers(this.props.list.records, this.props.layerKey);
    }

    layerLabel(index) {
        return sprintf(this.env._t("Layer %s"), index + 1);
    }

    isLocked(record) {
        return this.props.readonly || record.isReadonly(this.props.layerKey);
    }

    async onDrop({element, parent}) {
        if (!parent) {
            return;
        }
        const target =
            parent.dataset.layer === undefined
                ? {gap: Number(parent.dataset.gap)}
                : {layer: Number(parent.dataset.layer)};
        const plan = planDrop(this.layers, element.dataset.id, target, (record) =>
            this.isLocked(record)
        );
        if (plan.error) {
            this.notification.add(
                this.env._t("This move would shift a locked item; it was cancelled."),
                {type: "warning"}
            );
            return;
        }
        if (plan.updates.length) {
            await this.props.applyUpdates(plan.updates);
        }
    }
}
FlowRenderer.template = "web_widget_x2many_flow.FlowRenderer";
FlowRenderer.components = {FlowCard};
FlowRenderer.props = {
    list: Object,
    archInfo: Object,
    layerKey: String,
    titleColumn: {type: Object, optional: true},
    columns: Array,
    direction: String,
    canToggleDirection: Boolean,
    readonly: Boolean,
    canCreate: Boolean,
    canDelete: Boolean,
    onAdd: Function,
    onOpen: Function,
    onDelete: Function,
    onToggleDirection: Function,
    applyUpdates: Function,
};
