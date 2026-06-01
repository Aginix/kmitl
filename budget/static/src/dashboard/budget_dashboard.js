/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const DIMENSIONS = [
    { key: "department_analytic_id", code: "departments", label: "ส่วนงาน" },
    { key: "source_analytic_id", code: "sources", label: "แหล่งเงิน" },
    { key: "fund_analytic_id", code: "funds", label: "กองทุน" },
    { key: "activity_analytic_id", code: "activities", label: "กิจกรรม" },
];

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
        this.dimensions = DIMENSIONS;
        this.fiscalYears = [];
        this.rootAccounts = [];
        this.dimensionOptions = {};
        this.state = useState({
            fiscalYearId: false,
            rootAccountId: false,
            filters: {},
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
        for (const dim of DIMENSIONS) {
            this.dimensionOptions[dim.key] = await this.orm.searchRead(
                "account.analytic.account",
                [["root_plan_id.code", "=", dim.code]],
                ["id", "display_name"],
                { order: "display_name" }
            );
        }
        const today = new Date().toISOString().slice(0, 10);
        const covering = this.fiscalYears.find(
            (fy) => fy.date_from <= today && fy.date_to >= today
        );
        this.state.fiscalYearId = (covering || this.fiscalYears[0] || {}).id || false;
        await this.load();
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
                    { ...this.state.filters },
                ]
            );
            this.state.rows = data.rows || [];
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

    onDimChange(key, ev) {
        const value = parseInt(ev.target.value) || false;
        if (value) {
            this.state.filters[key] = value;
        } else {
            delete this.state.filters[key];
        }
        this.load();
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
        return Object.entries(this.state.filters).map(([key, value]) => [
            key,
            "=",
            value,
        ]);
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

BudgetDashboard.template = "budget.BudgetDashboard";

registry.category("actions").add("budget_dashboard", BudgetDashboard);
