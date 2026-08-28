/** @odoo-module */

import { ReceiptDashboard } from "../components/receipt_dashboard";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";

export class ReceiptListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    async onCreateReportClick() {
        const records = this.model.root.selection;
        const recordIds = records.length
            ? records.map((r) => r.resId)
            : [];
        if (!recordIds.length) {
            const allRecords = this.model.root.records;
            for (const rec of allRecords) {
                if (
                    rec.data.state === "confirmed" &&
                    !rec.data.remittance_id
                ) {
                    recordIds.push(rec.resId);
                }
            }
        }
        if (!recordIds.length) {
            return;
        }
        const action = await this.orm.call(
            "kmitl.receipt",
            "action_create_report",
            [recordIds]
        );
        await this.actionService.doAction(action);
    }
}

export class ReceiptDashboardListRenderer extends ListRenderer {}
ReceiptDashboardListRenderer.components = {
    ...ListRenderer.components,
    ReceiptDashboard,
};
ReceiptDashboardListRenderer.template = "receipt_kmitl.DashboardListRenderer";

registry.category("views").add("receipt_kmitl_dashboard_tree", {
    ...listView,
    buttonTemplate: "receipt_kmitl.ListButtons",
    Controller: ReceiptListController,
    Renderer: ReceiptDashboardListRenderer,
});
