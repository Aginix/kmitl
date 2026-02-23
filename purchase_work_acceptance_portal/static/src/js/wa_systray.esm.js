/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component, useState, onWillStart } = owl;

export class WaSystray extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");

        this.state = useState({
            items: [],
            totalCount: 0,
        });

        onWillStart(async () => {
            await this.fetchData();
        });

        useBus(this.env.bus, "wa_inbox_updated", () => {
            this.fetchData();
        });
    }

    async fetchData() {
        try {
            const result = await this.rpc("/web/dataset/call_kw/res.users/get_wa_inbox_count", {
                model: "res.users",
                method: "get_wa_inbox_count",
                args: [],
                kwargs: {},
            });
            this.state.items = result.items || [];
            this.state.totalCount = result.total_count || 0;
        } catch (error) {
            console.error("Failed to fetch WA inbox count:", error);
            this.state.items = [];
            this.state.totalCount = 0;
        }
    }

    onItemClick(item) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: item.name,
            res_model: "work.acceptance",
            res_id: item.id,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

WaSystray.template = "purchase_work_acceptance_portal.WaSystray";
WaSystray.components = { Dropdown, DropdownItem };

registry.category("systray").add(
    "purchase_work_acceptance_portal.WaSystray",
    { Component: WaSystray },
    { sequence: 91 }
);
