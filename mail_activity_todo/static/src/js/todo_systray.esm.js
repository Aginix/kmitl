/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component, useState, onWillStart } = owl;

export class TodoSystray extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            groups: [],
            totalCount: 0,
        });
        this.treeViewId = false;
        this.formViewId = false;

        onWillStart(async () => {
            await this.fetchData();
        });

        // Live refresh: the server pings "mail_activity_todo_updated" (via the
        // bus notification handler) whenever a Todo addressed to me changes.
        useBus(this.env.bus, "mail_activity_todo_updated", () => this.fetchData());
    }

    async fetchData() {
        try {
            const result = await this.orm.call("res.users", "get_my_todo_count", []);
            this.state.groups = result.groups || [];
            this.state.totalCount = result.total_count || 0;
            this.treeViewId = result.tree_view_id || false;
            this.formViewId = result.form_view_id || false;
        } catch (error) {
            console.error("Failed to fetch Todo count:", error);
            this.state.groups = [];
            this.state.totalCount = 0;
        }
    }

    onGroupClick(group) {
        // Drill into the Todo app (inbox) filtered to this source model.
        this.action.doAction({
            type: "ir.actions.act_window",
            name: group.name,
            res_model: "mail.activity",
            domain: [
                ["is_my_todo", "=", true],
                ["is_read_by_me", "=", false],
                ["todo_category", "!=", false],
                ["res_model_id", "=", group.model_id],
            ],
            views: [
                [this.treeViewId, "list"],
                [this.formViewId, "form"],
            ],
            target: "current",
        });
    }

    onViewAllClick() {
        this.action.doAction("mail_activity_todo.action_my_todos");
    }
}

TodoSystray.template = "mail_activity_todo.TodoSystray";
TodoSystray.components = { Dropdown, DropdownItem };

export const systrayItem = {
    Component: TodoSystray,
};

registry
    .category("systray")
    .add("mail_activity_todo.TodoSystray", systrayItem, { sequence: 95 });
