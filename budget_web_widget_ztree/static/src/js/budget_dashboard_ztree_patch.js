/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Ztree } from "@app_web_widget_ztree/js/ztree";
import { BudgetDashboard } from "@budget/dashboard/budget_dashboard";
import { BudgetReservationPicker } from "@budget/reservation_picker/budget_reservation_picker";

const DIM_ZTREE_OPTIONS = {
    parent_key: "parent_id",
    expend_level: "1",
    order: "code",
};

patch(BudgetDashboard, "budget_web_widget_ztree.BudgetDashboard.static", {
    components: { ...BudgetDashboard.components, Ztree },
});

patch(BudgetDashboard.prototype, "budget_web_widget_ztree.BudgetDashboard", {
    // Tree-shaped nodes (id/name/pId) straight from search_ztree, scoped to
    // the dimension's analytic plan — in place of the core's flat
    // {label, accountId} options built via searchRead. No "— ทั้งหมด —" node:
    // clearing the filter still goes through onDimInput (delete the input
    // text), same as before.
    sourcesFor(dim) {
        return [
            {
                options: (request) =>
                    this.orm.call("account.analytic.account", "search_ztree", [], {
                        ...DIM_ZTREE_OPTIONS,
                        domain: [["root_plan_id.code", "=", dim.code]],
                        search: request && request.trim() ? request.trim() : false,
                    }),
            },
        ];
    },

    // Wired as the Ztree component's `setting.callback.onClick` (see
    // ztree_dashboard_patch.xml) so a mouse click routes into the same
    // onDimSelect as the keyboard/Enter path (Ztree calls
    // props.onSelect(ev, {treeNode}) for both).
    ztreeSettingFor(dimKey) {
        return {
            callback: {
                onClick: (event, treeId, treeNode) =>
                    this.onDimSelect(dimKey, { treeNode }),
            },
        };
    },

    // Highlights the currently-selected node when the tree (re)opens.
    ztreeDataFor(dimKey) {
        return {
            ztree_model: "account.analytic.account",
            ztree_parent_key: "parent_id",
            ztree_expend_level: "1",
            ztree_selected_id: this.state.filters[dimKey] || false,
        };
    },

    onDimSelect(dimKey, params) {
        const node = params && params.treeNode;
        if (!node || node.action) {
            return;
        }
        this.state.filters[dimKey] = node.id;
        this.state.filterLabels[dimKey] = node.name;
        this.load();
    },
});

// The core picker's own sourcesFor exists only to strip the base dashboard's
// "— ทั้งหมด —" placeholder from the flat option list. That filter
// (`o.accountId`) doesn't apply to tree nodes, so once sourcesFor is
// tree-shaped it would just discard every option — bypass it and call the
// (patched) dashboard implementation directly.
patch(
    BudgetReservationPicker.prototype,
    "budget_web_widget_ztree.BudgetReservationPicker",
    {
        sourcesFor(dim) {
            return BudgetDashboard.prototype.sourcesFor.call(this, dim);
        },
    }
);
