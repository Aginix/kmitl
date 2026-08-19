/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
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
// Dimensions the row axis can be broken down by, in fixed nesting order (outer
// to inner); the budget-account tree always hangs off the innermost one.
const BREAKDOWN_ORDER = [
    { key: "department_analytic_id", label: "แจกแจงตามส่วนงาน" },
    { key: "activity_analytic_id", label: "แจกแจงตามกิจกรรม" },
    { key: "fund_analytic_id", label: "แจกแจงตามกองทุน" },
];
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
    "returned",
];
// Drill-down opens in a separate browser tab. A dynamic domain cannot survive
// Odoo's URL hash, so the action is stashed in localStorage under a one-shot
// key and re-hydrated by the budget_drilldown client action (bottom of file).
const DRILLDOWN_ACTION = "budget_drilldown";
const DRILLDOWN_PREFIX = "budget_drill_";
// Stage labels so each drill tab's breadcrumb names the column it came from.
const USAGE_LABELS = { reserve: "เงินจอง", obligate: "ผูกพัน", consume: "เบิกจ่าย" };

export class BudgetDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.hierDimensions = HIER_DIMENSIONS;
        this.breakdownOrder = BREAKDOWN_ORDER;
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
            breakdownDims: {
                department_analytic_id: true,
                activity_analytic_id: true,
                fund_analytic_id: true,
            },
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

    // The enabled breakdown dimensions in fixed nesting order (outer to inner).
    get breakdownList() {
        return this.breakdownOrder
            .filter((dim) => this.state.breakdownDims[dim.key])
            .map((dim) => dim.key);
    }

    async load() {
        if (!this.state.fiscalYearId) {
            this.state.rows = [];
            return;
        }
        this.state.loading = true;
        try {
            const breakdown = this.breakdownList;
            const data = await this.orm.call(
                "budget.dashboard",
                "get_dashboard_data",
                [
                    this.state.fiscalYearId,
                    this.state.rootAccountId || false,
                    this.effectiveFilters,
                    breakdown.length ? breakdown : false,
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

    // Toggle one breakdown dimension: the budget-account tree is nested under the
    // enabled dimensions (in fixed order). Drop stale collapse state (keys differ
    // between breakdown shapes).
    toggleBreakdown(dimKey) {
        this.state.breakdownDims[dimKey] = !this.state.breakdownDims[dimKey];
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
        // Dimension (breakdown) rows are tinted, with a shade per nesting depth.
        if (row.row_type === "dim") {
            parts.push("o_bd_dim", "o_bd_dim_" + (row.dim_level || 0));
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
        const skip = new Set(exclude || []);
        const leaves = [];
        for (const [key, value] of Object.entries(this.effectiveFilters)) {
            if (skip.has(key)) {
                continue;
            }
            leaves.push([key, key === SOURCE_KEY ? "=" : this.state.hierOp, value]);
        }
        return leaves;
    }

    // Per-row account + dimension constraints for a drill-down.
    //   - account row: exact-match EVERY breakdown dimension, then its account
    //     subtree (the exact tuple it sits under);
    //   - dimension group row: exact-match the ancestor dimensions, child_of its
    //     own dimension (its whole subtree), leave deeper dimensions free, and
    //     scope accounts to the report's expense roots.
    _drillLeaves(row) {
        const dims = this.breakdownList;
        if (!dims.length) {
            return [["account_id", "child_of", row.id]];
        }
        const dimId = (field) => (row.dims && row.dims[field]) || false;
        if (row.row_type === "account") {
            const leaves = dims.map((field) => [field, "=", dimId(field)]);
            leaves.push(["account_id", "child_of", row.account_id]);
            return leaves;
        }
        const ownLevel = row.dim_level || 0;
        const leaves = [];
        dims.forEach((field, i) => {
            if (i < ownLevel) {
                leaves.push([field, "=", dimId(field)]);
            } else if (i === ownLevel) {
                const id = dimId(field);
                leaves.push(id ? [field, "child_of", id] : [field, "=", false]);
            }
        });
        const accountScope = this.state.rootAccountId
            ? this.state.rootAccountId
            : this.rootAccounts.map((r) => r.id);
        if (!Array.isArray(accountScope) || accountScope.length) {
            leaves.push(["account_id", "child_of", accountScope]);
        }
        return leaves;
    }

    _drillName(row) {
        return `${row.code || ""} ${row.name || ""}`.trim();
    }

    // Breakdown dimensions are supplied per-row by _drillLeaves, so drop them
    // from the filter-bar domain to avoid a redundant/over-constraining leaf.
    get _drillExclude() {
        return this.breakdownList;
    }

    // Stash the act_window in localStorage (shared across same-origin tabs) and
    // open a one-shot client action that re-hydrates it. Done synchronously in
    // the click gesture so the tab is not blocked, with no server round-trip.
    _openDrill(name, resModel, domain) {
        const key =
            DRILLDOWN_PREFIX + Date.now() + "_" + Math.floor(Math.random() * 1e9);
        browser.localStorage.setItem(
            key,
            JSON.stringify({
                type: "ir.actions.act_window",
                name,
                res_model: resModel,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain,
                target: "current",
            })
        );
        browser.open(`/web#action=${DRILLDOWN_ACTION}&drill_key=${key}`, "_blank");
    }

    drillBudget(row, appropriationType) {
        const domain = [
            ["parent_state", "=", "posted"],
            ["account_fiscal_year_id", "=", this.state.fiscalYearId],
        ];
        let label;
        if (appropriationType) {
            // งบต้นปี: only the initial appropriation lines behind the figure.
            domain.push(["move_type", "=", "appropriation"]);
            domain.push(["appropriation_type", "=", appropriationType]);
            label = "งบต้นปี";
        } else {
            // งบปัจจุบัน: posted appropriation + entry lines (incl. transfers).
            domain.push(["move_type", "in", ["appropriation", "entry"]]);
            label = "งบปัจจุบัน";
        }
        domain.push(...this._drillLeaves(row), ...this._dimDomain(this._drillExclude));
        this._openDrill(
            `${this._drillName(row)} — ${label}`,
            "budget.move.line",
            domain
        );
    }

    drillUsage(row, moveType) {
        // Each usage column drills into only its own commitment-line type:
        // เงินจอง → reserve, ผูกพัน → obligate, เบิกจ่าย → consume. Note these
        // cells are net (e.g. ผูกพัน = Σobligate − Σconsume) while the drill
        // lists the gross lines of that one stage, so the list total need not
        // equal the cell — the column header documents the figure.
        const domain = [
            ["state", "=", "posted"],
            ["commitment_id.state", "in", ["reserved", "partial", "done"]],
            ["account_fiscal_year_id", "=", this.state.fiscalYearId],
            ["move_type", "=", moveType],
            ...this._drillLeaves(row),
            ...this._dimDomain(this._drillExclude),
        ];
        this._openDrill(
            `${this._drillName(row)} — ${USAGE_LABELS[moveType]}`,
            "budget.commitment.line",
            domain
        );
    }

    drillReturned(row) {
        // ส่งคืนเงินเหลือจ่าย drills into only the คืนจอง lines (negative
        // reserve flagged is_return), so the audit list shows exactly the
        // returns behind the figure and their source documents.
        const domain = [
            ["state", "=", "posted"],
            ["commitment_id.state", "in", ["reserved", "partial", "done"]],
            ["account_fiscal_year_id", "=", this.state.fiscalYearId],
            ["move_type", "=", "reserve"],
            ["is_return", "=", true],
            ...this._drillLeaves(row),
            ...this._dimDomain(this._drillExclude),
        ];
        this._openDrill(
            `${this._drillName(row)} — ส่งคืนเงินเหลือจ่าย`,
            "budget.commitment.line",
            domain
        );
    }
}

BudgetDashboard.components = { AutoComplete };
BudgetDashboard.template = "budget.BudgetDashboard";

registry.category("actions").add("budget_dashboard", BudgetDashboard);

// One-shot client action that re-hydrates a drill-down opened in a new tab.
// The dashboard stashed the act_window in localStorage under the key carried in
// the URL; we consume it once and hand it back to the action service.
registry.category("actions").add(DRILLDOWN_ACTION, (env, action) => {
    const key = (action.params && action.params.drill_key) || "";
    const raw = key && browser.localStorage.getItem(key);
    if (key) {
        browser.localStorage.removeItem(key);
    }
    // Stale link (e.g. the tab was reloaded after the key was consumed): fall
    // back to the dashboard rather than leaving a blank screen.
    return raw
        ? JSON.parse(raw)
        : { type: "ir.actions.client", tag: "budget_dashboard" };
});
