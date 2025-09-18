/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";

export class BudgetAppropriationLineRenderer extends ListRenderer {
    setup() {
        super.setup();
    }

    getTextNote(record) {
        return "asdfasdfijsaidfjioaj";
    }

    get note() {
        return "asdfasdfijsaidfjioaj";
    }

    getAllocationAmount(record) {
        return 0
    }

    getAvailableAmount(record) {
        return record.data.balance - this.getAllocationAmount(record)
    }
}
BudgetAppropriationLineRenderer.template =
    "budget_appropriation.BudgetAppropriationLineRenderer";
BudgetAppropriationLineRenderer.recordRowTemplate =
    "budget_appropriation.ListRenderer.RecordRow";

export class BudgetAppropriationLine extends X2ManyField {
    setup() {
        super.setup();
    }
}
BudgetAppropriationLine.components = {
    ...X2ManyField.components,
    ListRenderer: BudgetAppropriationLineRenderer,
};

registry.category("fields").add("budget_appropriation_line", BudgetAppropriationLine);
