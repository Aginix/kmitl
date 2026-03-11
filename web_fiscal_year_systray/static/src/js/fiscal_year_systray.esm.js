/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart } = owl;

export class FiscalYearSystray extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({ fiscalYearName: false });

        onWillStart(async () => {
            try {
                const name = await this.rpc("/web/dataset/call_kw/res.company/get_current_fiscal_year_name", {
                    model: "res.company",
                    method: "get_current_fiscal_year_name",
                    args: [],
                    kwargs: {},
                });
                this.state.fiscalYearName = name;
            } catch (error) {
                console.error("Failed to fetch current fiscal year:", error);
            }
        });
    }
}

FiscalYearSystray.template = "web_fiscal_year_systray.FiscalYearSystray";

registry.category("systray").add("web_fiscal_year_systray.FiscalYearSystray", {
    Component: FiscalYearSystray,
}, { sequence: 1 });
