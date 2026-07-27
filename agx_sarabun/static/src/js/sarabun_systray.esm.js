/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component, useState, onWillStart } = owl;

/**
 * e-Sarabun inbox tray (กล่องหนังสือเข้า).
 *
 * Lists the หนังสือ awaiting the current user's action — i.e. documents with an
 * *active* routing step whose snapshot holders include the user. Refreshes on
 * open (beforeOpen), on web-client load (onWillStart), and on the realtime bus
 * event "sarabun_inbox_updated" pushed by the engine when a step activates/clears.
 */
export class SarabunSystray extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            documents: [],
            totalCount: 0,
        });

        onWillStart(async () => {
            await this.fetchData();
        });

        // Realtime: the notification handler service re-broadcasts the bus event.
        useBus(this.env.bus, "sarabun_inbox_updated", () => {
            this.fetchData();
        });
    }

    async fetchData() {
        try {
            const result = await this.orm.call(
                "sarabun.document",
                "get_my_sarabun_inbox",
                []
            );
            this.state.documents = result.documents || [];
            this.state.totalCount = result.total_count || 0;
        } catch (error) {
            console.error("Failed to fetch e-Sarabun inbox:", error);
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
