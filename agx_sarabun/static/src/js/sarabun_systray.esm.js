/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component, useState, onWillStart } = owl;

export class SarabunSystray extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.state = useState({
            isOpen: false,
            groups: [],
            totalCount: 0,
        });
        onWillStart(async () => {
            await this.fetchData();
        });
    }

    async fetchData() {
        try {
            const result = await this.rpc("/web/dataset/call_kw/res.users/get_sarabun_inbox_count", {
                model: "res.users",
                method: "get_sarabun_inbox_count",
                args: [],
                kwargs: {},
            });
            this.state.groups = result.groups || [];
            this.state.totalCount = result.total_count || 0;
        } catch (error) {
            console.error("Failed to fetch Sarabun inbox count:", error);
            this.state.groups = [];
            this.state.totalCount = 0;
        }
    }

    async onDropdownToggle(isOpen) {
        this.state.isOpen = isOpen;
        if (isOpen) {
            await this.fetchData();
        }
    }

    onGroupClick(group) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Inbox - " + group.name,
            res_model: "sarabun.document.recipient",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["id", "in", group.recipient_ids]],
            target: "current",
        });
    }

    onViewAllClick() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Sarabun Inbox",
            res_model: "sarabun.document.recipient",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "new"]],
            context: { search_default_my_inbox: 1 },
            target: "current",
        });
    }
}

SarabunSystray.template = "agx_sarabun.SarabunSystray";
SarabunSystray.components = { Dropdown, DropdownItem };

export const systrayItem = {
    Component: SarabunSystray,
};

registry.category("systray").add("agx_sarabun.SarabunSystray", systrayItem, { sequence: 90 });
