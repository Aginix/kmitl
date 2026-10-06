/** @odoo-module **/

import {BudgetDashboard} from "@budget/dashboard/budget_dashboard";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";
import {toRaw} from "@odoo/owl";

patch(BudgetDashboard.prototype, "budget_dashboard_pool_tag.BudgetDashboard", {
    setup() {
        this._super(...arguments);
        // Registered Pool Tags (โครงการ/แผน) and which ones are shown.
        this.state.poolTags = [];
        this.state.poolTagOn = {};
        this._poolTagSeq = 0;
    },

    async onWillStart() {
        // Capture _super before awaiting: the patch helper unbinds it after
        // the synchronous part of the call.
        const _super = this._super.bind(this);
        this.state.poolTags = await this.orm.call(
            "budget.dashboard",
            "get_pool_tags",
            []
        );
        for (const tag of this.state.poolTags) {
            this.state.poolTagOn[tag.field] = true;
        }
        await _super();
    },

    get enabledPoolTags() {
        return this.state.poolTags
            .filter((tag) => this.state.poolTagOn[tag.field])
            .map((tag) => tag.field);
    },

    async load() {
        const _super = this._super.bind(this);
        const seq = ++this._poolTagSeq;
        await _super();
        const tagFields = this.enabledPoolTags;
        if (!this.state.fiscalYearId || !tagFields.length || !this.state.rows.length) {
            return;
        }
        const breakdown = this.breakdownList;
        const items = await this.orm.call("budget.dashboard", "get_pool_tag_rows", [
            this.state.fiscalYearId,
            this.state.rootAccountId || false,
            this.effectiveFilters,
            breakdown.length ? breakdown : false,
            tagFields,
        ]);
        // A newer load started meanwhile: its rows are not ours to splice into.
        if (seq !== this._poolTagSeq || !items.length) {
            return;
        }
        this._splicePoolTagRows(items, breakdown);
    },

    // Hang each item right under its budget-account row (matched by account +
    // breakdown tuple), before that account's child accounts.
    _splicePoolTagRows(items, breakdown) {
        const matchKey = (accountId, dims) =>
            [accountId, ...breakdown.map((d) => (dims && dims[d]) || 0)].join("|");
        const byAccount = {};
        for (const item of items) {
            const key = matchKey(item.account_id, item.dims);
            (byAccount[key] = byAccount[key] || []).push(item);
        }
        const rows = [];
        for (const row of toRaw(this.state.rows)) {
            rows.push(row);
            if (row.row_type !== "account") {
                continue;
            }
            const own = byAccount[matchKey(row.account_id, row.dims)];
            if (!own) {
                continue;
            }
            row.has_children = true;
            for (const item of own) {
                rows.push({
                    ...item,
                    id: false,
                    key: `${row.key}|t${item.tag_field || "none"}${
                        item.analytic_id || 0
                    }`,
                    parent_key: row.key,
                    level: row.level + 1,
                });
            }
        }
        this.state.rows = rows;
    },

    togglePoolTag(field) {
        this.state.poolTagOn[field] = !this.state.poolTagOn[field];
        this.state.collapsed = {};
        this.load();
    },

    get visibleRows() {
        // Search also matches item (project / plan) code or name.
        const query = (this.state.accountSearch || "").trim().toLowerCase();
        if (!query) {
            return this._super();
        }
        return this._rowsWithAncestors(
            (row) =>
                (row.row_type === "account" || row.row_type === "pool_tag") &&
                ((row.code || "").toLowerCase().includes(query) ||
                    (row.name || "").toLowerCase().includes(query))
        );
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
