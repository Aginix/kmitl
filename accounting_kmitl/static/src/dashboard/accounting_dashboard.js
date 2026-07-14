/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
// Reuse the ECharts OWL wrapper shipped by the ``budget`` module (a hard
// dependency of accounting_kmitl), so no charting library is added here.
import { EChart } from "@budget/overview/echart";

// Landing "work launchpad" for the Accounting app: a grid of KPI cards that
// each open a filtered list, plus quick-create buttons. The cards (labels,
// colours, domains and counts) are fully defined by the
// accounting.kmitl.dashboard server model, so other modules can add cards
// without touching this component.
//
// Below the cards it also shows a "most-used expense codes" horizontal bar
// chart, filterable by fiscal year (the filter scopes the chart only -- the
// cards stay live operational queues).
export class AccountingDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: { currency_symbol: "", cards: [] },
            fiscalYears: [],
            fiscalYearId: false,
            expense: { items: [] },
            expenseLoading: true,
            analytics: { aging: { ap: [], ar: [] }, forecast: [], top_vendors: [] },
            analyticsLoading: true,
        });

        onWillStart(async () => {
            this.state.fiscalYears = await this.orm.searchRead(
                "account.fiscal.year",
                [],
                ["id", "name", "date_from", "date_to"],
                { order: "date_from desc" }
            );
            // Default to the fiscal year covering today, else the latest one,
            // else "All" (no fiscal year records) -- mirrors budget_overview.
            const today = new Date().toISOString().slice(0, 10);
            const covering = this.state.fiscalYears.find(
                (fy) => fy.date_from <= today && fy.date_to >= today
            );
            this.state.fiscalYearId =
                (covering || this.state.fiscalYears[0] || {}).id || false;

            const [data] = await Promise.all([
                this.orm.call(
                    "accounting.kmitl.dashboard",
                    "get_dashboard_data",
                    []
                ),
                this.loadExpense(),
                this.loadAnalytics(),
            ]);
            this.state.data = data;
            this.state.loading = false;
        });
    }

    // Current-state cash & payables analytics (not fiscal-year scoped).
    async loadAnalytics() {
        this.state.analytics = await this.orm.call(
            "accounting.kmitl.dashboard",
            "get_analytics",
            []
        );
        this.state.analyticsLoading = false;
    }

    // Reload just the expense chart for the currently selected fiscal year.
    async loadExpense() {
        this.state.expenseLoading = true;
        this.state.expense = await this.orm.call(
            "accounting.kmitl.dashboard",
            "get_expense_frequency",
            [this.state.fiscalYearId || false]
        );
        this.state.expenseLoading = false;
    }

    onPeriodChange(ev) {
        this.state.fiscalYearId = parseInt(ev.target.value) || false;
        this.loadExpense();
    }

    // Cards as delivered by the server, in display order.
    get cards() {
        return [...(this.state.data.cards || [])].sort(
            (a, b) => a.sequence - b.sequence
        );
    }

    get text() {
        return {
            title: _t("Accounting Dashboard"),
            subtitle: _t("Overview of pending work and outstanding balances"),
            quickActions: _t("Quick actions"),
            newVendorBill: _t("New vendor bill"),
            newCustomerInvoice: _t("New customer invoice"),
            newJournalEntry: _t("New journal entry"),
            expenseTitle: _t("Most-used expense codes"),
            fiscalYear: _t("Fiscal year"),
            all: _t("All"),
            noData: _t("No data"),
            agingTitle: _t("Payables / receivables aging"),
            forecastTitle: _t("Payment forecast"),
            topVendorsTitle: _t("Top vendors by amount due"),
        };
    }

    // Compact currency-agnostic number for chart axes/labels (e.g. 1.2M, 340K).
    _compact(value) {
        const n = value || 0;
        const abs = Math.abs(n);
        if (abs >= 1e6) {
            return (n / 1e6).toFixed(1) + "M";
        }
        if (abs >= 1e3) {
            return (n / 1e3).toFixed(0) + "K";
        }
        return String(Math.round(n));
    }

    // AP vs AR outstanding balance, grouped by overdue-days bucket.
    get agingChartOption() {
        const aging = this.state.analytics.aging || { ap: [], ar: [] };
        const labels = [_t("Not due"), "1-30", "31-60", "61-90", "90+"];
        const payables = _t("Payables");
        const receivables = _t("Receivables");
        return {
            tooltip: {
                trigger: "axis",
                axisPointer: { type: "shadow" },
                valueFormatter: (v) => this.formatAmount(v),
            },
            legend: { data: [payables, receivables], bottom: 0 },
            grid: { left: 8, right: 16, top: 16, bottom: 40, containLabel: true },
            xAxis: { type: "category", data: labels },
            yAxis: {
                type: "value",
                axisLabel: { formatter: (v) => this._compact(v) },
            },
            series: [
                {
                    name: payables,
                    type: "bar",
                    itemStyle: { color: "#d97706" },
                    data: aging.ap,
                },
                {
                    name: receivables,
                    type: "bar",
                    itemStyle: { color: "#3b82f6" },
                    data: aging.ar,
                },
            ],
        };
    }

    // Outstanding payables bucketed by days until due (bucket 0 = overdue, red).
    get forecastChartOption() {
        const forecast = this.state.analytics.forecast || [];
        const labels = [_t("Overdue"), "0-7", "8-30", "31-60", "61-90", "90+"];
        return {
            tooltip: {
                trigger: "axis",
                axisPointer: { type: "shadow" },
                valueFormatter: (v) => this.formatAmount(v),
            },
            grid: { left: 8, right: 16, top: 16, bottom: 24, containLabel: true },
            xAxis: { type: "category", data: labels },
            yAxis: {
                type: "value",
                axisLabel: { formatter: (v) => this._compact(v) },
            },
            series: [
                {
                    type: "bar",
                    data: forecast.map((value, i) => ({
                        value,
                        itemStyle: { color: i === 0 ? "#dc3545" : "#15803d" },
                    })),
                    barMaxWidth: 40,
                },
            ],
        };
    }

    // Top vendors by outstanding payable (horizontal bar, highest on top).
    get topVendorsChartOption() {
        const rev = [...(this.state.analytics.top_vendors || [])].reverse();
        const sym = this.state.data.currency_symbol || "";
        return {
            grid: { left: 8, right: 72, top: 8, bottom: 8, containLabel: true },
            tooltip: {
                trigger: "axis",
                axisPointer: { type: "shadow" },
                valueFormatter: (v) => sym + this.formatAmount(v),
            },
            xAxis: {
                type: "value",
                axisLabel: { formatter: (v) => this._compact(v) },
            },
            yAxis: {
                type: "category",
                data: rev.map((v) => v.name),
                axisLabel: { fontSize: 11, width: 160, overflow: "truncate" },
            },
            series: [
                {
                    type: "bar",
                    data: rev.map((v) => v.amount),
                    itemStyle: { color: "#d97706" },
                    barMaxWidth: 22,
                    label: {
                        show: true,
                        position: "right",
                        formatter: (p) => this._compact(p.value),
                    },
                },
            ],
        };
    }

    // ECharts option for the Top-N most-used expense codes (horizontal bar).
    // Items arrive sorted desc; ECharts draws a category axis bottom-up, so we
    // reverse to put rank #1 on top.
    get expenseChartOption() {
        const rev = [...(this.state.expense.items || [])].reverse();
        const docWord = _t("documents");
        return {
            grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
            tooltip: {
                trigger: "axis",
                axisPointer: { type: "shadow" },
                formatter: (ps) => {
                    const it = rev[ps[0].dataIndex];
                    return `<strong>${it.code}</strong><br/>${it.name}<br/>${ps[0].value} ${docWord}`;
                },
            },
            xAxis: { type: "value", minInterval: 1 },
            yAxis: {
                type: "category",
                data: rev.map((i) => i.name),
                axisLabel: { fontSize: 11, width: 180, overflow: "truncate" },
            },
            series: [
                {
                    type: "bar",
                    data: rev.map((i) => i.count),
                    itemStyle: { color: "#3b82f6" },
                    barMaxWidth: 22,
                    label: { show: true, position: "right" },
                },
            ],
        };
    }

    formatAmount(value) {
        return (value || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    // Open the card's model filtered to exactly its domain, so the list
    // contents match the number shown on the card.
    openCard(card) {
        if (!card.domain) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: card.title,
            res_model: card.res_model,
            domain: card.domain,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    // Quick-create: open a blank account.move form of the requested type.
    newDoc(moveType) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            views: [[false, "form"]],
            target: "current",
            context: { default_move_type: moveType },
        });
    }
}

AccountingDashboard.template = "accounting_kmitl.AccountingDashboard";
AccountingDashboard.components = { EChart };

registry.category("actions").add("accounting_kmitl.dashboard", AccountingDashboard);
