/** @odoo-module **/

import {Component, onMounted, onWillStart, onWillUnmount, useState} from "@odoo/owl";

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

import {
    dashboardBoxColorRegistry,
    dashboardChartRegistry,
} from "@purchase_request_dashboard/dashboard_registry";
import {
    CHART_COLORS,
    formatCurrency,
    formatNumber,
    makeDoughnutOption,
    makeStackedBarOption,
    makeStackedLineOption,
    pieDrilldownDomain,
} from "@purchase_request_dashboard/utils";

export class PurchaseRequestDashboard extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false,
        };

        this.rpc = useService("rpc");
        this.action = useService("action");

        // Built-in cards live alongside registered ones and are sorted by sequence
        // so extensions can slot their cards anywhere in the grid.
        this.builtinCards = [
            {
                id: "prChart1",
                title: "ประเภทการจัดซื้อจัดจ้าง (รายเดือน)",
                sequence: 10,
                update: () => this._updateChart1(),
            },
            {
                id: "prChart2",
                title: "ประเภทการจัดซื้อจัดจ้าง",
                sequence: 20,
                update: () => this._updateChart2(),
            },
            {
                id: "prChart4",
                title: "แนวโน้มการอนุมัติจัดซื้อจัดจ้าง",
                sequence: 40,
                update: () => this._updateChart4(),
            },
            {
                id: "prChart5",
                title: "ประเภทการจัดซื้อจัดจ้าง (ตามส่วนงาน)",
                sequence: 50,
                update: () => this._updateChart5(),
            },
        ];

        this.state = useState({
            filters: {
                fiscal_year_id: null,
                source_id: null,
            },
            loading: false,
            selectedStates: [],
            summaryBoxes: [],
            chart1Data: {months: [], series: []},
            chart2Data: [],
            chart4Data: {months: [], series: []},
            chart5Data: {departments: [], series: []},
            filterOptions: {
                fiscal_years: [],
                sources: [],
            },
        });

        // ECharts instances keyed by card id — covers both built-in and registered.
        this._chartInstances = new Map();
        // Extension endpoint results keyed by card id.
        this._extensionData = new Map();

        this._onResize = () => {
            for (const chart of this._chartInstances.values()) {
                if (chart) chart.resize();
            }
        };

        onWillStart(async () => {
            await this._loadECharts();
            await this.loadData();
        });

        onMounted(() => {
            this._renderAllCharts();
            window.addEventListener("resize", this._onResize);
        });

        onWillUnmount(() => {
            window.removeEventListener("resize", this._onResize);
            this._disposeCharts();
        });
    }

    // ──────────────────────────────────────────────────────────────────
    // Card layout (built-in + registered, sorted by sequence, 3 per row)
    // ──────────────────────────────────────────────────────────────────

    get chartCards() {
        const registered = dashboardChartRegistry
            .getEntries()
            .map(([, entry]) => entry);
        return [...this.builtinCards, ...registered].sort(
            (a, b) => (a.sequence || 0) - (b.sequence || 0)
        );
    }

    get chartCardRows() {
        const cards = this.chartCards;
        const rows = [];
        for (let i = 0; i < cards.length; i += 3) {
            rows.push(cards.slice(i, i + 3));
        }
        return rows;
    }

    // ──────────────────────────────────────────────────────────────────
    // ECharts loading & lifecycle
    // ──────────────────────────────────────────────────────────────────

    /**
     * Load ECharts from CDN on demand.
     * ECharts is not bundled in Odoo's asset pipeline, so we load it
     * via a script tag the first time the dashboard is opened.
     */
    async _loadECharts() {
        if (typeof echarts !== "undefined") {
            return;
        }
        return new Promise((resolve) => {
            const script = document.createElement("script");
            script.src =
                "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js";
            script.onload = resolve;
            script.onerror = () => {
                console.error("Failed to load ECharts");
                resolve();
            };
            document.head.appendChild(script);
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            // Core is called first because on the initial load the frontend has
            // no fiscal_year_id/source_id yet — the core endpoint chooses those
            // defaults and returns them. Extensions then use the resolved
            // filters so their queries match what the core is showing.
            const coreResponse = await this.rpc(
                "/purchase_request/dashboard/data",
                {
                    fiscal_year_id: this.state.filters.fiscal_year_id,
                    source_id: this.state.filters.source_id,
                    selected_states: this.state.selectedStates,
                }
            );

            this.state.filterOptions = coreResponse.filter_options;
            this.state.filters = coreResponse.filters;
            this.state.summaryBoxes = coreResponse.summary_boxes;
            this.state.chart1Data = coreResponse.chart1_purchase_type_by_month;
            this.state.chart2Data = coreResponse.chart2_purchase_type_pie;
            this.state.chart4Data = coreResponse.chart4_approved_trend;
            this.state.chart5Data = coreResponse.chart5_purchase_type_by_dept;

            await this._loadExtensionData({
                fiscal_year_id: coreResponse.filters.fiscal_year_id,
                source_id: coreResponse.filters.source_id,
                selected_states: this.state.selectedStates,
            });
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
            this._renderAllCharts();
        }
    }

    /**
     * Fetch data for every registered extension card in parallel.
     * Extensions that share endpoints incur one RPC per card — acceptable given
     * the current small chart count and simpler contract.
     */
    async _loadExtensionData(payload) {
        const entries = dashboardChartRegistry.getEntries();
        await Promise.all(
            entries.map(async ([id, entry]) => {
                try {
                    const data = await this.rpc(entry.endpoint, payload);
                    this._extensionData.set(id, data);
                } catch (err) {
                    console.error(`Extension chart '${id}' failed:`, err);
                    this._extensionData.set(id, null);
                }
            })
        );
    }

    _renderAllCharts() {
        // Defer to let OWL commit the DOM before we hand nodes to ECharts.
        setTimeout(() => {
            for (const card of this.chartCards) {
                if (card.update) {
                    card.update();
                } else {
                    this._renderRegisteredCard(card);
                }
            }
        }, 100);
    }

    _renderRegisteredCard(card) {
        const chart = this._getOrCreateChart(card.id);
        if (!chart) return;
        const data = this._extensionData.get(card.id);
        if (data === undefined || data === null) return;
        card.render(chart, data, {
            filters: this.state.filters,
            selectedStates: this.state.selectedStates,
            action: this.action,
            utils: {
                CHART_COLORS,
                formatCurrency,
                makeStackedBarOption,
                makeStackedLineOption,
                makeDoughnutOption,
                pieDrilldownDomain,
            },
        });
    }

    _disposeCharts() {
        for (const chart of this._chartInstances.values()) {
            if (chart) chart.dispose();
        }
        this._chartInstances.clear();
    }

    /**
     * Get or create an ECharts instance for a given DOM element.
     *
     * OWL may re-render the DOM at any time, which orphans the old chart container.
     * We detect this by checking if the existing chart's DOM element is still in the
     * document. If not, we dispose the stale instance and create a new one.
     */
    _getOrCreateChart(domId) {
        if (typeof echarts === "undefined") {
            return null;
        }
        const chartDom = document.getElementById(domId);
        if (!chartDom) {
            return null;
        }
        let chart = this._chartInstances.get(domId);
        if (chart) {
            const existingDom = chart.getDom();
            if (
                !existingDom ||
                !document.body.contains(existingDom) ||
                existingDom !== chartDom
            ) {
                chart.dispose();
                chart = null;
            }
        }
        if (!chart) {
            chart = echarts.init(chartDom);
            this._chartInstances.set(domId, chart);
        }
        return chart;
    }

    // ──────────────────────────────────────────────────────────────────
    // Built-in chart renderers
    // ──────────────────────────────────────────────────────────────────

    _updateChart1() {
        const chart = this._getOrCreateChart("prChart1");
        if (!chart) return;
        const data = this.state.chart1Data;
        chart.setOption(makeStackedBarOption(data, data.months || []), true);
    }

    _updateChart2() {
        const chart = this._getOrCreateChart("prChart2");
        if (!chart) return;
        this._renderPieDrilldown({
            chart,
            data: this.state.chart2Data,
            seriesName: "ประเภทการจัดซื้อจัดจ้าง",
            getDrilldownFilter: (params) => {
                const id = params.data.procurement_type_id;
                return id ? ["procurement_type_id", "=", id] : null;
            },
        });
    }

    _updateChart4() {
        const chart = this._getOrCreateChart("prChart4");
        if (!chart) return;
        const data = this.state.chart4Data;
        chart.setOption(makeStackedLineOption(data, data.months || []), true);
    }

    _updateChart5() {
        const chart = this._getOrCreateChart("prChart5");
        if (!chart) return;
        const data = this.state.chart5Data;
        const deptAxisOpts = {
            axisLabel: {rotate: 30, overflow: "truncate", width: 80},
        };
        chart.setOption(
            makeStackedBarOption(data, data.departments || [], deptAxisOpts),
            true
        );
    }

    /**
     * Shared doughnut renderer with click-through to a filtered list view.
     * Extension charts can reuse this via `utils.makeDoughnutOption` +
     * `utils.pieDrilldownDomain` in their own render() body.
     */
    _renderPieDrilldown({chart, data, seriesName, getDrilldownFilter}) {
        const pieData = (data || []).map((item, i) => ({
            ...item,
            itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
        }));

        chart.setOption(makeDoughnutOption(seriesName, pieData), true);

        chart.off("click");
        chart.on("click", (params) => {
            const extraFilter = getDrilldownFilter(params);
            if (!extraFilter) return;
            this.action.doAction({
                type: "ir.actions.act_window",
                name: params.name,
                res_model: "purchase.request",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain: pieDrilldownDomain(
                    this.state.filters,
                    this.state.selectedStates,
                    extraFilter
                ),
                target: "current",
            });
        });
    }

    // ──────────────────────────────────────────────────────────────────
    // Event handlers
    // ──────────────────────────────────────────────────────────────────

    onFiscalYearChange(ev) {
        const value = ev.target.value;
        this.state.filters.fiscal_year_id = value ? parseInt(value, 10) : null;
        this.loadData();
    }

    onSourceChange(ev) {
        const value = ev.target.value;
        this.state.filters.source_id = value ? parseInt(value, 10) : null;
        this.loadData();
    }

    onBoxClick(stateKey) {
        if (stateKey === "total") return;
        const idx = this.state.selectedStates.indexOf(stateKey);
        if (idx >= 0) {
            this.state.selectedStates.splice(idx, 1);
        } else {
            this.state.selectedStates.push(stateKey);
        }
        this.loadData();
    }

    isBoxSelected(stateKey) {
        return this.state.selectedStates.includes(stateKey);
    }

    // ──────────────────────────────────────────────────────────────────
    // Template helpers
    // ──────────────────────────────────────────────────────────────────

    /** Compare filter option ID with current selection (string comparison for select elements). */
    isFilterSelected(optionId, currentId) {
        return String(optionId) === String(currentId);
    }

    formatCurrency(amount) {
        return formatCurrency(amount);
    }

    formatNumber(num) {
        return formatNumber(num);
    }

    getBoxColorClass(state) {
        const builtinClasses = {
            draft: "text-dark",
            to_verify: "text-info",
            to_approve: "text-warning",
            in_approval: "text-warning",
            in_progress: "text-primary",
            done: "text-success",
            cancelled: "text-secondary",
            rejected: "text-danger",
            total: "text-primary",
        };
        const extended = dashboardBoxColorRegistry.contains(state)
            ? dashboardBoxColorRegistry.get(state)
            : null;
        return extended || builtinClasses[state] || "text-secondary";
    }
}

PurchaseRequestDashboard.template =
    "purchase_request_dashboard.PurchaseRequestDashboard";
PurchaseRequestDashboard.components = {
    ControlPanel,
};

registry
    .category("actions")
    .add("purchase_request_dashboard", PurchaseRequestDashboard);
