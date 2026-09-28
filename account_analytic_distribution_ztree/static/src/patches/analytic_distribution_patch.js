/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AnalyticDistribution } from "@analytic/components/analytic_distribution/analytic_distribution";
import { Ztree } from "@app_web_widget_ztree/js/ztree";

const ZTREE_SEARCH_LIMIT = 1000;

patch(AnalyticDistribution, "account_analytic_distribution_ztree.static", {
    components: { ...AnalyticDistribution.components, Ztree },
});

patch(AnalyticDistribution.prototype, "account_analytic_distribution_ztree", {
    planHasZtree(groupId) {
        const plan = this.allPlans.find((p) => p.id === groupId);
        return !!(plan && plan.use_ztree_widget);
    },

    // Tree-shaped nodes (id/name/pId) via search_ztree, scoped exactly like
    // sourcesAnalyticAccount, so the field renders parent/child accounts as
    // an expandable tree instead of a flat autocomplete list.
    sourcesAnalyticTree(groupId) {
        return [
            {
                options: (request) =>
                    this.orm.call("account.analytic.account", "search_ztree", [], {
                        domain: this.analyticAccountDomain(groupId),
                        parent_key: "parent_id",
                        expend_level: 1,
                        order: "code",
                        display_field: "display_name",
                        limit: ZTREE_SEARCH_LIMIT,
                        search: request && request.trim() ? request.trim() : false,
                    }),
            },
        ];
    },

    ztreeDataFor(tag) {
        return {
            ztree_model: "account.analytic.account",
            ztree_parent_key: "parent_id",
            ztree_expend_level: 1,
            ztree_selected_id: tag.analytic_account_id || 0,
        };
    },

    // Wired as the Ztree component's `setting.callback.onClick` so a mouse
    // click routes into the same selection as the keyboard/Enter path
    // (Ztree calls props.onSelect(ev, {treeNode}) for both).
    ztreeSettingFor(tag) {
        return {
            callback: {
                onClick: (event, treeId, treeNode) =>
                    this.onZtreeSelect(tag, { treeNode }),
            },
        };
    },

    onZtreeSelect(tag, params) {
        const node = params && params.treeNode;
        if (!node || node.action) {
            return;
        }
        tag.analytic_account_id = node.id;
        tag.analytic_account_name = node.selected_name || node.name;
        this.setFocusSelector(`.tag_${tag.id} .o_analytic_percentage`);
        this.autoFill();
    },
});
