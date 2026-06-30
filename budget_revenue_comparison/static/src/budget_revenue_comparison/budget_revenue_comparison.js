/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import { MultiRecordSelect } from "./multi_record_select";

const REPORT_MODEL = "budget.revenue.comparison.report";

// Selected-record state buckets that feed the report options (the four KMITL
// accounting dimensions).
const SELECTION_KEYS = ["departments", "sources", "funds", "activities"];

export class BudgetRevenueComparison extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.fiscalYears = [];
        this.state = useState({
            fiscalYearId: false,
            dateFrom: false,
            dateTo: false,
            onlyPosted: true,
            groupByDepartment: false,
            departments: [],
            sources: [],
            funds: [],
            activities: [],
            rows: [],
            loading: false,
        });
        this.labels = {
            departments: _t("Departments"),
            sources: _t("Sources"),
            funds: _t("Funds"),
            activities: _t("Activities"),
        };
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        this.companyId = this.company.currentCompany.id;
        this.fiscalYears = await this.orm.searchRead(
            "account.fiscal.year",
            [],
            ["id", "name", "date_from", "date_to"],
            { order: "date_from desc" }
        );
        const today = new Date().toISOString().slice(0, 10);
        const covering = this.fiscalYears.find(
            (fy) => fy.date_from <= today && fy.date_to >= today
        );
        const fy = covering || this.fiscalYears[0];
        if (fy) {
            this.state.fiscalYearId = fy.id;
            this.state.dateFrom = fy.date_from;
            this.state.dateTo = fy.date_to;
        } else {
            const year = new Date().getFullYear();
            this.state.dateFrom = `${year}-01-01`;
            this.state.dateTo = `${year}-12-31`;
        }
        await this.load();
    }

    // ------------------------------------------------------------------
    // Report options + data loading
    // ------------------------------------------------------------------
    get options() {
        return {
            company_id: this.companyId,
            fiscal_year_id: this.state.fiscalYearId,
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            only_posted: this.state.onlyPosted,
            group_by_department: this.state.groupByDepartment,
            dims: {
                departments: this.state.departments.map((r) => r.id),
                sources: this.state.sources.map((r) => r.id),
                funds: this.state.funds.map((r) => r.id),
                activities: this.state.activities.map((r) => r.id),
            },
        };
    }

    async load() {
        if (!this.state.fiscalYearId) {
            this.state.rows = [];
            return;
        }
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                REPORT_MODEL,
                "get_comparison_data",
                [this.options]
            );
            this.state.rows = data.rows || [];
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------
    // Filter events
    // ------------------------------------------------------------------
    onFiscalYearChange(ev) {
        const id = parseInt(ev.target.value) || false;
        this.state.fiscalYearId = id;
        const fy = this.fiscalYears.find((f) => f.id === id);
        if (fy) {
            this.state.dateFrom = fy.date_from;
            this.state.dateTo = fy.date_to;
        }
        this.load();
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value || false;
        this.load();
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value || false;
        this.load();
    }

    onTogglePosted(ev) {
        this.state.onlyPosted = ev.target.checked;
        this.load();
    }

    onToggleGroupByDept(ev) {
        this.state.groupByDepartment = ev.target.checked;
        this.load();
    }

    onSelectionChange(key, selected) {
        if (SELECTION_KEYS.includes(key)) {
            this.state[key] = selected;
            this.load();
        }
    }

    // ------------------------------------------------------------------
    // Rendering helpers
    // ------------------------------------------------------------------
    formatAmount(value) {
        if (value === null || value === undefined) {
            return "";
        }
        return value.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    formatPercentage(value) {
        if (value === null || value === undefined) {
            return "–";
        }
        return (
            value.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }) + "%"
        );
    }

    async exportXlsx() {
        const action = await this.orm.call(REPORT_MODEL, "action_export_xlsx", [
            this.options,
        ]);
        await this.action.doAction(action);
    }
}

BudgetRevenueComparison.template = "budget_revenue_comparison.BudgetRevenueComparison";
BudgetRevenueComparison.components = { MultiRecordSelect };

registry.category("actions").add("budget_revenue_comparison", BudgetRevenueComparison);
