/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component, useState, onWillStart } = owl;

export class WorkflowNotificationSystray extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            items: [],
            unreadCount: 0,
        });

        onWillStart(async () => {
            await this.fetchData();
        });

        useBus(this.env.bus, "workflow_notification_updated", () => this.fetchData());
    }

    async fetchData() {
        try {
            const result = await this.orm.call(
                "mail.thread",
                "get_workflow_notifications",
                []
            );
            this.state.items = result.items || [];
            this.state.unreadCount = result.unread_count || 0;
        } catch (error) {
            console.error("Failed to fetch workflow notifications:", error);
            this.state.items = [];
            this.state.unreadCount = 0;
        }
    }

    onItemClick(item) {
        if (!item.res_model || !item.res_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: item.res_model,
            res_id: item.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onMarkAllRead() {
        await this.orm.call("mail.thread", "action_mark_workflow_notifications_read", []);
        await this.fetchData();
    }

    formatDate(isoDate) {
        if (!isoDate) return "";
        const d = new Date(isoDate);
        const now = new Date();
        const diffMs = now - d;
        const diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return "เมื่อสักครู่";
        if (diffMin < 60) return `${diffMin} นาทีที่แล้ว`;
        const diffHr = Math.floor(diffMin / 60);
        if (diffHr < 24) return `${diffHr} ชั่วโมงที่แล้ว`;
        const diffDay = Math.floor(diffHr / 24);
        return `${diffDay} วันที่แล้ว`;
    }
}

WorkflowNotificationSystray.template =
    "mail_workflow_notification.WorkflowNotificationSystray";
WorkflowNotificationSystray.components = { Dropdown, DropdownItem };

export const systrayItem = {
    Component: WorkflowNotificationSystray,
};

registry
    .category("systray")
    .add("mail_workflow_notification.WorkflowNotificationSystray", systrayItem, {
        sequence: 94,
    });
