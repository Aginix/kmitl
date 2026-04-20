/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";

const { Component, useState, onWillStart } = owl;

export class WaSystray extends Component {
    setup() {
        this.orm = useService("orm");

        this.state = useState({
            items: [],
            totalCount: 0,
            showAll: false,
        });

        onWillStart(() => this.fetchData());

        useBus(this.env.bus, "wa_inbox_updated", () => this.fetchData());
    }

    async fetchData() {
        try {
            const method = this.state.showAll ? "get_wa_inbox_all" : "get_wa_inbox_count";
            const result = await this.orm.call("res.users", method, [], {});
            this.state.items = result.items || [];
            this.state.totalCount = result.total_count || 0;
        } catch {
            this.state.items = [];
            this.state.totalCount = 0;
        }
    }

    async markRead(item) {
        await this.orm.call("work.acceptance.inbox", "action_mark_read", [[item.id]]);
        await this.fetchData();
    }

    async markAllRead() {
        await this.orm.call("res.users", "mark_all_wa_read", [], {});
        this.state.showAll = false;
        await this.fetchData();
    }

    async showAllItems() {
        this.state.showAll = true;
        await this.fetchData();
    }

    async showUnreadOnly() {
        this.state.showAll = false;
        await this.fetchData();
    }
}

WaSystray.template = "purchase_work_acceptance_portal.WaSystray";
WaSystray.components = { Dropdown };

registry.category("systray").add(
    "purchase_work_acceptance_portal.WaSystray",
    { Component: WaSystray },
    { sequence: 91 }
);
