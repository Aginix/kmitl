/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ApprovalCategoryTreeRenderer } from "@agx_approval_dashboard_tree/views/category_tree.esm";

const { useState } = owl;

patch(ApprovalCategoryTreeRenderer.prototype, "agx_approval_dashboard_tree_favorite", {
    setup() {
        this._super(...arguments);
        this.favState = useState({});
    },

    _allRecords() {
        const list = this.props.list;
        return list.isGrouped
            ? list.groups.flatMap((group) => group.list.records)
            : list.records;
    },

    _recordById(catId) {
        return this._allRecords().find((record) => record.resId === catId);
    },

    isFavorite(catId) {
        if (catId in this.favState) {
            return this.favState[catId];
        }
        const record = this._recordById(catId);
        return (record && record.data.is_favorite) || false;
    },

    get favoriteCategories() {
        const categories = [];
        for (const record of this._allRecords()) {
            if (!this.isFavorite(record.resId)) {
                continue;
            }
            const budgetAccount = record.data.budget_account_id;
            categories.push({
                id: record.resId,
                name: record.data.name,
                sequence: record.data.sequence || 0,
                budgetAccountName: budgetAccount ? budgetAccount[1] : false,
            });
        }
        categories.sort(
            (a, b) => a.sequence - b.sequence || a.name.localeCompare(b.name)
        );
        return categories;
    },

    async toggleFavorite(catId) {
        const newValue = !this.isFavorite(catId);
        this.favState[catId] = newValue;
        try {
            await this.orm.call("approval.category", "toggle_favorite", [catId]);
        } catch (error) {
            this.favState[catId] = !newValue;
            throw error;
        }
    },
});
