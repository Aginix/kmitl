/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, useState } = owl;

export class ApprovalCategoryTreeRenderer extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ manualOpen: {} });
        this.groupOrder = new Map();
        onWillStart(async () => {
            const groups = await this.orm.searchRead(
                "approval.category.group",
                [],
                ["id"],
                { order: "sequence, name" }
            );
            this.groupOrder = new Map(groups.map((g, i) => [g.id, i]));
        });
    }

    get searchActive() {
        const searchModel = this.env.searchModel;
        return !!(searchModel && searchModel.query && searchModel.query.length);
    }

    get categoryGroups() {
        const list = this.props.list;
        const records = list.isGrouped
            ? list.groups.flatMap((group) => group.list.records)
            : list.records;
        const byGroup = new Map();
        for (const record of records) {
            const groupValue = record.data.group_id;
            const groupId = groupValue ? groupValue[0] : 0;
            if (!byGroup.has(groupId)) {
                byGroup.set(groupId, {
                    id: groupId,
                    name: groupValue ? groupValue[1] : "-",
                    categories: [],
                });
            }
            byGroup.get(groupId).categories.push({
                id: record.resId,
                name: record.data.name,
                sequence: record.data.sequence || 0,
            });
        }
        const groups = [...byGroup.values()];
        for (const group of groups) {
            group.categories.sort(
                (a, b) => a.sequence - b.sequence || a.name.localeCompare(b.name)
            );
        }
        groups.sort(
            (a, b) =>
                (this.groupOrder.get(a.id) ?? Number.MAX_SAFE_INTEGER) -
                (this.groupOrder.get(b.id) ?? Number.MAX_SAFE_INTEGER)
        );
        return groups;
    }

    isOpen(groupId) {
        return this.state.manualOpen[groupId] ?? this.searchActive;
    }

    toggle(groupId) {
        this.state.manualOpen[groupId] = !this.isOpen(groupId);
    }

    async openCategory(categoryId) {
        const action = await this.orm.call("approval.category", "create_request", [categoryId]);
        this.action.doAction(action);
    }
}
ApprovalCategoryTreeRenderer.template = "agx_approval_dashboard_tree.CategoryTree";

registry.category("views").add("approval_category_tree", {
    ...listView,
    Renderer: ApprovalCategoryTreeRenderer,
});
