/** @odoo-module **/

import {registry} from "@web/core/registry";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {NoteLineRenderer} from "@budget/components/note_line/note_line.esm";
import {useService} from "@web/core/utils/hooks";
import {useState, onWillStart} from "@odoo/owl";

export class CustomeNoteLineRenderer extends NoteLineRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.procurementData = useState({});
        onWillStart(() => this._loadProcurementPlans());
    }
    formattedAmount(value) {
        return new Intl.NumberFormat("en-US").format(value);
    }
    async _loadProcurementPlans() {
        try {
            const plans = await this.orm.searchRead("procurement.plan", [], []);
            for (const plan of plans) {
                this.procurementData[plan.id] = plan;
            }
        } catch (error) {
            console.error("ไม่สามารถโหลดแผนจัดซื้อจัดจ้างได้", error);
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
