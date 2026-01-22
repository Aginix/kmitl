/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component, useState, onWillStart } = owl;

export class SarabunSystray extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");

        this.state = useState({
            documents: [],
            totalCount: 0,
        });

        onWillStart(async () => {
            await this.fetchData();
        });

        // Listen for real-time bus notifications via sarabunNotificationHandler service
        useBus(this.env.bus, "sarabun_inbox_updated", () => {
            this.fetchData();
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
            this.state.documents = result.documents || [];
            this.state.totalCount = result.total_count || 0;
        } catch (error) {
            console.error("Failed to fetch Sarabun inbox count:", error);
            this.state.documents = [];
            this.state.totalCount = 0;
        }
    }

    onDocumentClick(doc) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: doc.subject || doc.name,
            res_model: "sarabun.document",
            res_id: doc.id,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    onViewAllClick() {
        this.action.doAction("agx_sarabun.action_sarabun_document_inbox");
    }
}

SarabunSystray.template = "agx_sarabun.SarabunSystray";
SarabunSystray.components = { Dropdown, DropdownItem };

export const systrayItem = {
    Component: SarabunSystray,
};

registry.category("systray").add("agx_sarabun.SarabunSystray", systrayItem, { sequence: 90 });
