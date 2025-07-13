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
            draftPlans: [],
            draftMap: new Map(),
        });
        onWillStart(() => this._loadProcurementPlans());
        onWillUpdateProps((nextProps) => this.updateProp(nextProps));
    }
    updateProp(props) {
        const records = props.list.records[1].data.procurement_plan_ids.records; // ยังทำให้ทำทีละ record ไม่ได้
        const draftPlans = records.filter((r) => r.data.state === "draft");
        const draftMap = new Map();
        for (const rec of draftPlans) {
            const planId = rec.data.id;
            if (this.procurementData.hasOwnProperty(planId)) {
                this.procurementData[rec.data.id] = rec.data;
                console.log("เข้าเงื่อนไข draftMap", rec.data.id);
            } else {
                console.log("ไม่เข้าเงื่อนไข draftMap", rec.data.id);
                draftMap.set(rec.data.id, rec);
            }
        }
        this.procurementData.draftPlans = draftPlans;
        this.procurementData.draftMap = draftMap;
        console.log("testttt =====>", props)
        if(draftPlans.length === 0) {
            this._loadProcurementPlans();
        }
    }

    formattedAmount(value) {
        return new Intl.NumberFormat("en-US").format(value);
    }
    async _loadProcurementPlans() {
        const plans = await this.orm.searchRead("procurement.plan", [], []);
        for (const plan of plans) {
            this.procurementData[plan.id] = plan;
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
