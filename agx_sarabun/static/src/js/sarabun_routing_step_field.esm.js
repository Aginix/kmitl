/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { makeContext } from "@web/core/context";

/**
 * Custom One2many widget for routing_step_ids.
 *
 * The tree uses editable="bottom" so the handle widget's drag-drop resequence
 * properly persists on save.  This widget restores the modal-form behaviour
 * that a non-editable tree would give: "Add a line" opens the step form dialog
 * and clicking an existing row opens it in the dialog (not inline).
 */
export class SarabunRoutingStepField extends X2ManyField {
    async onAdd({ context } = {}) {
        const record = this.props.record;
        context = makeContext([record.getFieldContext(this.props.name), context]);
        return this._openRecord({ context });
    }

    get rendererProps() {
        const props = super.rendererProps;
        // Disable inline editing so row clicks open the form dialog.
        // canResequenceRows only checks `readonly` (not `editable`),
        // so handle drag-drop still works.
        props.editable = false;
        return props;
    }
}

SarabunRoutingStepField.displayName = "Sarabun Routing Steps";
registry.category("fields").add("sarabun_routing_step_one2many", SarabunRoutingStepField);
