/** @odoo-module **/

import {registry} from "@web/core/registry";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {NoteLineRenderer} from "@budget/components/note_line/note_line.esm";
import {useService} from "@web/core/utils/hooks";
import {useState, onWillStart, onWillUpdateProps} from "@odoo/owl";

export class CustomeNoteLineRenderer extends NoteLineRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.procurementData = useState({
            records: new Map(),
            plan: [],
        });
        onWillStart(() => this._loadProcurementPlans());
        onWillUpdateProps((nextProps) => this.updateProp(nextProps));
    }

    async updateProp(props) {
        const records = props.list.records;
        // search all records in appropiration_lines
        for (const record of records) {
            const procurementPlanIds = record.data.procurement_plan_ids.records;
            // check if procurement_plan_ids state change to draft
            const draftPlans = procurementPlanIds.filter(
                (r) => r.data.state === "draft"
            );

            // check if form save
            if (draftPlans.length === 0) {
                const plans = await this.orm.searchRead(
                    "procurement.plan",
                    [["budget_move_line_id", "=", record.data.id]],
                    []
                );
                for (const plan of plans) {
                    this.procurementData[plan.id] = plan;
                }
            }

            for (const plan of procurementPlanIds) {
                if (plan.data.state === "draft") {
                    this.procurementData.plan.push(plan.data);
                } else {
                    this.procurementData.plan.push(this.procurementData[plan.data.id]);
                }
            }
            this.procurementData.records.set(record.data.id, this.procurementData.plan);
            this.procurementData.plan = [];
        }
    }

    formattedAmount(value) {
        return new Intl.NumberFormat("en-US").format(value);
    }

    // loading ครั้งแรก
    async _loadProcurementPlans() {
        const plans = await this.orm.searchRead("procurement.plan", [], []);
        for (const plan of plans) {
            this.procurementData[plan.id] = plan;
        }

        const records = this.props.list.records;
        for (const record of records) {
            const procurementPlanIds = record.data.procurement_plan_ids.records;

            for (const plan of procurementPlanIds) {
                if (plan.data.state === "draft") {
                    this.procurementData.plan.push(plan.data);
                } else {
                    this.procurementData.plan.push(this.procurementData[plan.data.id]);
                }
            }

            this.procurementData.records.set(record.data.id, this.procurementData.plan);
            this.procurementData.plan = [];
        }
    }
}
CustomeNoteLineRenderer.template = "budget_procurement_plan.NoteLineRenderer";
CustomeNoteLineRenderer.recordRowTemplate =
    "budget_procurement_plan.ListRenderer.RecordRow";

export class CustomBudgetLine extends X2ManyField {
    setup() {
        super.setup();
    }
}
CustomBudgetLine.components = {
    ...X2ManyField.components,
    ListRenderer: CustomeNoteLineRenderer,
};

registry.category("fields").add("custom_budget_line", CustomBudgetLine);
