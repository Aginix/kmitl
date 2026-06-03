/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component, useState, onWillStart } = owl;

export class TodoSystray extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");

        this.state = useState({
            todos: [],
            totalCount: 0,
        });

        onWillStart(async () => {
            await this.fetchData();
        });
    }

    async fetchData() {
        try {
            const result = await this.rpc("/web/dataset/call_kw/res.users/get_my_todo_count", {
                model: "res.users",
                method: "get_my_todo_count",
                args: [],
                kwargs: {},
            });
            this.state.todos = result.todos || [];
            this.state.totalCount = result.total_count || 0;
        } catch (error) {
            console.error("Failed to fetch Todo count:", error);
            this.state.todos = [];
            this.state.totalCount = 0;
        }
    }

    onTodoClick(todo) {
        // Jump to the source record — the load-bearing feature of the inbox.
        this.action.doAction({
            type: "ir.actions.act_window",
            name: todo.summary || todo.res_name,
            res_model: todo.res_model,
            res_id: todo.res_id,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    onViewAllClick() {
        this.action.doAction("kmitl_todo.action_my_todos");
    }
}

TodoSystray.template = "kmitl_todo.TodoSystray";
TodoSystray.components = { Dropdown, DropdownItem };

export const systrayItem = {
    Component: TodoSystray,
};

registry.category("systray").add("kmitl_todo.TodoSystray", systrayItem, { sequence: 95 });
