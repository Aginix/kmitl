/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, onWillStart } from "@odoo/owl";

class AssetReportDownload extends Component {
    setup() {
        onWillStart(async () => {
            const { url, filename } = this.props.action.params;
            const response = await fetch(url);
            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = blobUrl;
            link.download = filename || "report.xlsx";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(blobUrl);
            this.env.services.action.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: "account.asset",
                    view_mode: "list,form",
                    views: [[false, "list"], [false, "form"]],
                },
                { clearBreadcrumbs: true }
            );
        });
    }
}
AssetReportDownload.template = xml`<div/>`;

registry.category("actions").add("asset_report_download", AssetReportDownload);
