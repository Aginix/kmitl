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
                [this.state.fiscalYearId, this.state.rootAccountId || false, this.effectiveFilters]
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

    toggleRow(row) {
        if (row.has_children) {
            this.state.collapsed[row.id] = !this.state.collapsed[row.id];
        }
    }

    get rowsById() {
        const byId = {};
        for (const row of this.state.rows) {
            byId[row.id] = row;
        }
        return byId;
    }

    get visibleRows() {
        const byId = this.rowsById;
        const collapsed = this.state.collapsed;
        const hiddenByCollapse = (row) => {
            let pid = row.parent_id;
            while (pid) {
                if (collapsed[pid]) {
                    return true;
                }
                pid = byId[pid] ? byId[pid].parent_id : false;
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

    _dimDomain() {
        const leaves = [];
        for (const [key, value] of Object.entries(this.effectiveFilters)) {
            leaves.push([key, key === SOURCE_KEY ? "=" : this.state.hierOp, value]);
        }
        return leaves;
    }

    drillBudget(row) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `${row.code} ${row.name}`,
            res_model: "budget.move.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [
                ["parent_state", "=", "posted"],
                ["account_fiscal_year_id", "=", this.state.fiscalYearId],
                ["account_id", "child_of", row.id],
                ["move_type", "in", ["appropriation", "entry"]],
                ...this._dimDomain(),
            ],
            target: "current",
        });
    }

    drillUsage(row) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `${row.code} ${row.name}`,
            res_model: "budget.commitment.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [
                ["state", "=", "posted"],
                ["commitment_id.state", "in", ["reserved", "partial", "done"]],
                ["account_fiscal_year_id", "=", this.state.fiscalYearId],
                ["account_id", "child_of", row.id],
                ...this._dimDomain(),
            ],
            target: "current",
        });
    }
}

BudgetDashboard.components = { AutoComplete };
BudgetDashboard.template = "budget.BudgetDashboard";

registry.category("actions").add("budget_dashboard", BudgetDashboard);
