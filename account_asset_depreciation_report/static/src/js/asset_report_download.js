/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";

class AssetReportDownload extends Component {
    setup() {
        const url = this.props.action.params.url;
        const link = document.createElement("a");
        link.href = url;
        link.click();
        this.env.services.action.doAction({ type: "ir.actions.act_window_close" });
    }
}
AssetReportDownload.template = xml`<div/>`;

registry.category("actions").add("asset_report_download", AssetReportDownload);
