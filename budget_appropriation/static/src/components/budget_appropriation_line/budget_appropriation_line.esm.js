/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";

export class BudgetAppropriationLineRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    onDeleteRecord(record) {
        const accountName = record.data.account_id
            ? record.data.account_id[1]
            : "";
        const balance = record.data.balance || 0;
        const balanceFormatted = balance.toLocaleString("th-TH", {
            minimumFractionDigits: 2,
        });
        this.dialog.add(ConfirmationDialog, {
            title: "ยืนยันการลบรายการ",
            body: `คุณต้องการลบรายการ "${accountName}" จำนวนเงิน ${balanceFormatted} บาท ใช่หรือไม่?`,
            confirm: () => super.onDeleteRecord(record),
        });
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
