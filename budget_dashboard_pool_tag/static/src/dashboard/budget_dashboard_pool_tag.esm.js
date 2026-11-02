/** @odoo-module **/

import {BudgetDashboard} from "@budget/dashboard/budget_dashboard";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";

const DASHBOARD_TEMPLATE = "budget.BudgetDashboard";

patch(BudgetDashboard.prototype, "budget_dashboard_pool_tag.BudgetDashboard", {
    setup() {
        this._super(...arguments);
        // Registered Pool Tags (โครงการ/แผน), shown or hidden together.
        this.state.poolTags = [];
        this.state.showPoolTags = true;
    },

    async onWillStart() {
        // Capture _super before awaiting: the patch helper unbinds it after
        // the synchronous part of the call.
        const _super = this._super.bind(this);
        // Only the dashboard lists items; subclasses with their own template
        // (the reservation picker) skip the lookup. The tags only label the
        // toggle, so they load alongside the base start-up searches.
        const tags =
            this.constructor.template === DASHBOARD_TEMPLATE
                ? this.orm.call("budget.dashboard", "get_pool_tags", [])
                : Promise.resolve([]);
        await _super();
        this.state.poolTags = await tags;
    },

    // Item rows come back with the report rows (same RPC, same queries).
    get dashboardContext() {
        const context = this._super();
        return this.constructor.template === DASHBOARD_TEMPLATE
            ? {...context, pool_tag_rows: true}
            : context;
    },

    async load() {
        const _super = this._super.bind(this);
        await _super();
        this._applyPoolTagCarets();
    },

    get poolTagToggleLabel() {
        return `แสดงรายการ${this.state.poolTags.map((tag) => tag.label).join("/")}`;
    },

    // Hiding items is client-side only: no reload, collapse state kept.
    togglePoolTags() {
        this.state.showPoolTags = !this.state.showPoolTags;
        this._applyPoolTagCarets();
    },

    // A code whose only children are items shows its caret with the items.
    _applyPoolTagCarets() {
        for (const row of this.state.rows) {
            if (row.pool_tag_leaf) {
                row.has_children = this.state.showPoolTags;
            }
        }
    },

    get visibleRows() {
        // Search also matches item (project / plan) code or name, and a
        // matched budget code keeps its items.
        const query = (this.state.accountSearch || "").trim().toLowerCase();
        const matches = (row) =>
            (row.code || "").toLowerCase().includes(query) ||
            (row.name || "").toLowerCase().includes(query);
        const byKey = query ? this.rowsByKey : {};
        const rows = query
            ? this._rowsWithAncestors((row) => {
                  if (row.row_type === "account") {
                      return matches(row);
                  }
                  if (row.row_type !== "pool_tag") {
                      return false;
                  }
                  const code = byKey[row.parent_key];
                  return matches(row) || Boolean(code && matches(code));
              })
            : this._super();
        return this.state.showPoolTags
            ? rows
            : rows.filter((row) => row.row_type !== "pool_tag");
    },

    rowClass(row) {
        const cls = this._super(row);
        return row.row_type === "pool_tag" ? `${cls} o_bd_pool_tag`.trim() : cls;
    },

    // Item figures are not drill targets.
    drillBudget(row) {
        if (row.row_type !== "pool_tag") {
            return this._super(...arguments);
        }
    },

    drillUsage(row) {
        if (row.row_type !== "pool_tag") {
            return this._super(...arguments);
        }
    },

    drillReturned(row) {
        if (row.row_type !== "pool_tag") {
            return this._super(...arguments);
        }
    },

    openPoolTagRecord(row) {
        if (row.res_model && row.res_id) {
            browser.open(
                `/web#model=${row.res_model}&id=${row.res_id}&view_type=form`,
                "_blank"
            );
        }
    },
});
