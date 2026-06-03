/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Component, onWillStart, useState } from "@odoo/owl";

// ส่วนงาน / กองทุน / กิจกรรม are hierarchical analytic dimensions (autocomplete).
const HIER_DIMENSIONS = [
    { key: "department_analytic_id", code: "departments", label: "ส่วนงาน" },
    { key: "fund_analytic_id", code: "funds", label: "กองทุน" },
    { key: "activity_analytic_id", code: "activities", label: "กิจกรรม" },
];
// แหล่งเงิน is a flat, single, mandatory filter (defaults to source code "2").
const SOURCE_KEY = "source_analytic_id";
const DEFAULT_SOURCE_CODE = "2";
// Fixed display order for the expense budget-category (root) dropdown.
const ROOT_ORDER = ["51000", "52000", "53000", "54000", "55000", "07020"];
const VALUE_KEYS = [
    "initial",
    "current",
    "cap",
    "reserved",
    "obligated",
    "consumed",
    "used",
    "remaining",
];

export class BudgetDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.hierDimensions = HIER_DIMENSIONS;
        this.fiscalYears = [];
        this.rootAccounts = [];
        this.sources = [];

        // Honour incoming context defaults so a form button can open this report
        // pre-scoped, e.g. context={'default_fiscal_year_id': ..., 'default_source_analytic_id': ...}.
        const ctx = (this.props.action && this.props.action.context) || {};
        const ctxFilters = {};
        for (const dim of HIER_DIMENSIONS) {
            if (ctx["default_" + dim.key]) {
                ctxFilters[dim.key] = ctx["default_" + dim.key];
            }
        }
        this.state = useState({
            fiscalYearId: ctx.default_fiscal_year_id || false,
            rootAccountId: ctx.default_root_account_id || false,
            sourceId: ctx.default_source_analytic_id || false,
            filters: ctxFilters,
            filterLabels: {},
            hierOp: "=",
            rows: [],
            collapsed: {},
            hideZero: true,
            groupByActivity: false,
            loading: false,
        });
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        this.fiscalYears = await this.orm.searchRead(
            "account.fiscal.year",
            [],
            ["id", "name", "date_from", "date_to"],
            { order: "date_from desc" }
        );
        this.rootAccounts = await this.orm.searchRead(
            "budget.account",
            [["budget_type", "=", "expense"], ["parent_id", "=", false]],
            ["id", "code", "name"],
            { order: "code" }
        );
        // Apply the fixed display order; any root not listed is appended (by code).
        const rootRank = (code) => {
            const idx = ROOT_ORDER.indexOf(code);
            return idx === -1 ? ROOT_ORDER.length : idx;
        };
        this.rootAccounts.sort(
            (a, b) =>
                rootRank(a.code) - rootRank(b.code) || a.code.localeCompare(b.code)
        );
        this.sources = await this.orm.searchRead(
            "account.analytic.account",
            [["root_plan_id.code", "=", "sources"]],
            ["id", "display_name", "code"],
            { order: "code" }
        );
        if (!this.state.fiscalYearId) {
            const today = new Date().toISOString().slice(0, 10);
            const covering = this.fiscalYears.find(
                (fy) => fy.date_from <= today && fy.date_to >= today
            );
            this.state.fiscalYearId = (covering || this.fiscalYears[0] || {}).id || false;
        }
        if (!this.state.sourceId) {
            const def =
                this.sources.find((s) => s.code === DEFAULT_SOURCE_CODE) ||
                this.sources[0];
            this.state.sourceId = (def || {}).id || false;
        }
        // resolve display labels for any context-provided dimension filters
        for (const dim of HIER_DIMENSIONS) {
            const id = this.state.filters[dim.key];
            if (id) {
                const recs = await this.orm.read(
                    "account.analytic.account",
                    [id],
                    ["display_name"]
                );
                this.state.filterLabels[dim.key] = recs.length
                    ? recs[0].display_name
                    : "";
            }
        }
        await this.load();
    }

    get effectiveFilters() {
        const filters = { ...this.state.filters };
        if (this.state.sourceId) {
            filters[SOURCE_KEY] = this.state.sourceId;
        }
        return filters;
    }

    async load() {
        if (!this.state.fiscalYearId) {
            this.state.rows = [];
            return;
        }
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "budget.dashboard",
                "get_dashboard_data",
                [
                    this.state.fiscalYearId,
                    this.state.rootAccountId || false,
                    this.effectiveFilters,
                    this.state.groupByActivity ? "activity_analytic_id" : false,
                ]
            );
            this.state.rows = data.rows || [];
            this.state.hierOp = data.hier_op || "=";
        } finally {
            this.state.loading = false;
        }
    }

    onFiscalYearChange(ev) {
        this.state.fiscalYearId = parseInt(ev.target.value) || false;
        this.load();
    }

    onRootChange(ev) {
        this.state.rootAccountId = parseInt(ev.target.value) || false;
        this.load();
    }

    onSourceChange(ev) {
        this.state.sourceId = parseInt(ev.target.value) || false;
        this.load();
    }

    sourcesFor(dim) {
        return [
            {
                options: async (request) => {
                    const domain = [["root_plan_id.code", "=", dim.code]];
                    if (request) {
                        // Search stored fields only — display_name is a non-stored
                        // computed field, so an ilike on it is silently dropped
                        // (becomes TRUE) and the filter has no effect.
                        domain.push(
                            "|",
                            ["name", "ilike", request],
                            ["code", "ilike", request]
                        );
                    }
                    const recs = await this.orm.searchRead(
                        "account.analytic.account",
                        domain,
                        ["id", "display_name"],
                        { limit: 20, order: "code" }
                    );
                    const options = recs.map((r) => ({
                        label: r.display_name,
                        accountId: r.id,
                    }));
                    options.unshift({ label: "— ทั้งหมด —", accountId: false });
                    return options;
                },
            },
        ];
    }

    onDimSelect(dimKey, option) {
        if (option.accountId) {
            this.state.filters[dimKey] = option.accountId;
            this.state.filterLabels[dimKey] = option.label;
        } else {
            delete this.state.filters[dimKey];
            this.state.filterLabels[dimKey] = "";
        }
        this.load();
    }

    onDimInput(dimKey, args) {
        if (!args.inputValue) {
            this.state.filterLabels[dimKey] = "";
            if (this.state.filters[dimKey]) {
                delete this.state.filters[dimKey];
                this.load();
            }
        }
    }

    toggleHideZero() {
        this.state.hideZero = !this.state.hideZero;
    }

    // Toggle the activity breakdown: the budget-account tree is nested under the
    // activity hierarchy. Drop stale collapse state (keys differ between modes).
    toggleBreakdown() {
        this.state.groupByActivity = !this.state.groupByActivity;
        this.state.collapsed = {};
        this.load();
    }

    toggleRow(row) {
        if (row.has_children) {
            this.state.collapsed[row.key] = !this.state.collapsed[row.key];
        }
    }

    rowClass(row) {
        const parts = [];
        if (row.has_children) {
            parts.push("o_bd_group");
        }
        if (row.row_type === "activity") {
            parts.push("o_bd_activity");
        }
        return parts.join(" ");
    }

    get rowsByKey() {
        const byKey = {};
        for (const row of this.state.rows) {
            byKey[row.key] = row;
        }
        return byKey;
    }

    get visibleRows() {
        const byKey = this.rowsByKey;
        const collapsed = this.state.collapsed;
        const hiddenByCollapse = (row) => {
            let pk = row.parent_key;
            while (pk) {
                if (collapsed[pk]) {
                    return true;
                }
                pk = byKey[pk] ? byKey[pk].parent_key : false;
            }
            return false;
        };
        let rows = this.state.rows.filter((row) => !hiddenByCollapse(row));
        if (this.state.hideZero) {
            rows = rows.filter((row) => this.hasValue(row));
        }
        return rows;
    }

    hasValue(row) {
        return VALUE_KEYS.some((key) => Math.abs(row[key] || 0) > 0.005);
    }

    format(value) {
        return (value || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    _dimDomain(exclude) {
        const leaves = [];
        for (const [key, value] of Object.entries(this.effectiveFilters)) {
            if (key === exclude) {
                continue;
            }
            leaves.push([key, key === SOURCE_KEY ? "=" : this.state.hierOp, value]);
        }
        return leaves;
    }

    // Per-row account + activity constraints for a drill-down. In breakdown mode
    // an account row is scoped to its *exact* activity; an activity group row
    // covers its whole subtree (and every account under the chosen root).
    _drillLeaves(row) {
        if (!this.state.groupByActivity) {
            return [["account_id", "child_of", row.id]];
        }
        if (row.row_type === "activity") {
            // Group row: its whole activity subtree, scoped to the same expense
            // accounts the report aggregates (the selected root, else every
            // expense root — never the revenue side).
            const leaves = [
                row.activity_id
                    ? ["activity_analytic_id", "child_of", row.activity_id]
                    : ["activity_analytic_id", "=", false],
            ];
            const accountScope = this.state.rootAccountId
                ? this.state.rootAccountId
                : this.rootAccounts.map((r) => r.id);
            if (!Array.isArray(accountScope) || accountScope.length) {
                leaves.push(["account_id", "child_of", accountScope]);
            }
            return leaves;
        }
        // Account row: its account subtree for the exact tagged activity.
        return [
            ["account_id", "child_of", row.account_id],
            row.activity_id
                ? ["activity_analytic_id", "=", row.activity_id]
                : ["activity_analytic_id", "=", false],
        ];
    }

    _drillName(row) {
        return `${row.code || ""} ${row.name || ""}`.trim();
    }

    get _drillExclude() {
        return this.state.groupByActivity ? "activity_analytic_id" : undefined;
    }

    drillBudget(row) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this._drillName(row),
            res_model: "budget.move.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [
                ["parent_state", "=", "posted"],
                ["account_fiscal_year_id", "=", this.state.fiscalYearId],
                ["move_type", "in", ["appropriation", "entry"]],
                ...this._drillLeaves(row),
                ...this._dimDomain(this._drillExclude),
            ],
            target: "current",
        });
    }

    drillUsage(row) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this._drillName(row),
            res_model: "budget.commitment.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [
                ["state", "=", "posted"],
                ["commitment_id.state", "in", ["reserved", "partial", "done"]],
                ["account_fiscal_year_id", "=", this.state.fiscalYearId],
                ...this._drillLeaves(row),
                ...this._dimDomain(this._drillExclude),
            ],
            target: "current",
        });
    }
}

BudgetDashboard.components = { AutoComplete };
BudgetDashboard.template = "budget.BudgetDashboard";

registry.category("actions").add("budget_dashboard", BudgetDashboard);
