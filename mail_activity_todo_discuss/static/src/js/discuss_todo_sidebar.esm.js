/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { useService, useBus } from "@web/core/utils/hooks";

const { useState, onWillStart } = owl;

/**
 * The Todo section in the Discuss sidebar: a collapsible "Todos" header with the
 * open Todos grouped by source app (live counts via res.users.get_my_todo_count,
 * the same payload the systray uses). Clicking the header opens the full Todo
 * page in the main pane; clicking an app group opens it filtered to that app.
 * Active highlighting tracks the shared discuss.isTodoActive / todoResModel.
 */
export class DiscussTodoSidebar extends LegacyComponent {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({ groups: [], totalCount: 0, isOpen: true });

        onWillStart(() => this.fetchData());
        useBus(this.env.bus, "mail_activity_todo_updated", () => this.fetchData());
    }

    get discuss() {
        return this.props.record.discuss;
    }

    async fetchData() {
        try {
            const result = await this.orm.call("res.users", "get_my_todo_count", []);
            this.state.groups = result.groups || [];
            this.state.totalCount = result.total_count || 0;
        } catch (error) {
            console.error("Failed to fetch Todo groups:", error);
            this.state.groups = [];
            this.state.totalCount = 0;
        }
    }

    toggle() {
        this.state.isOpen = !this.state.isOpen;
    }

    onClickAll() {
        this.discuss.openTodos();
    }

    onClickGroup(group) {
        this.discuss.openTodos(group.model);
    }
}

Object.assign(DiscussTodoSidebar, {
    props: { record: Object },
    template: "mail_activity_todo_discuss.DiscussTodoSidebar",
});

registerMessagingComponent(DiscussTodoSidebar);
