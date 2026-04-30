/** @odoo-module **/

import {Component, onMounted, onWillStart, onWillUnmount, useState} from "@odoo/owl";

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

const CHART_COLORS = [
    "#5470c6",
    "#91cc75",
    "#fac858",
    "#ee6666",
    "#73c0de",
    "#3ba272",
    "#fc8452",
    "#9a60b4",
    "#ea7ccc",
    "#48b8d0",
];

export class PurchaseRequestDashboard extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false,
        };

        this.rpc = useService("rpc");
        this.action = useService("action");

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
            expensePieData: [],
            chart3Data: {months: [], series: []},
            chart4Data: {months: [], series: []},
            chart5Data: {departments: [], series: []},
            chart6Data: {departments: [], series: []},
            leadtimeHeatmap: [],
            filterOptions: {
                fiscal_years: [],
                sources: [],
            },
        });

        // ECharts instances (one per chart card)
        this.chart1 = null;
        this.chart2 = null;
        this.chartExpensePie = null;
        this.chart3 = null;
        this.chart4 = null;
        this.chart5 = null;
        this.chart6 = null;
        this.chartLeadtime = null;

        this._chartProps = [
            "chart1", "chart2", "chartExpensePie",
            "chart3", "chart4", "chart5", "chart6",
            "chartLeadtime",
        ];

        this._onResize = () => {
            for (const prop of this._chartProps) {
                if (this[prop]) this[prop].resize();
            }
        };

        onWillStart(async () => {
            await this._loadECharts();
            await this.loadData();
        });

        onMounted(() => {
            this._initCharts();
            window.addEventListener("resize", this._onResize);
        });

        onWillUnmount(() => {
            window.removeEventListener("resize", this._onResize);
            this._disposeCharts();
        });
    }

    // ──────────────────────────────────────────────────────────────────
    // Chart card definitions (used by XML t-foreach)
    // ──────────────────────────────────────────────────────────────────

    get chartCards() {
        return [
            {id: "prChart1", title: "ประเภทการจัดซื้อจัดจ้าง (รายเดือน)"},
            {id: "prChart2", title: "ประเภทการจัดซื้อจัดจ้าง"},
            {id: "prChartExpPie", title: "ประเภทค่าใช้จ่าย"},
            {id: "prChart3", title: "ประเภทค่าใช้จ่าย (รายเดือน)"},
            {id: "prChart4", title: "แนวโน้มการอนุมัติจัดซื้อจัดจ้าง"},
            {id: "prChart5", title: "ประเภทการจัดซื้อจัดจ้าง (ตามส่วนงาน)"},
            {id: "prChart6", title: "ประเภทค่าใช้จ่าย (ตามส่วนงาน)"},
            {id: "prChartLeadtime", title: "leadtime"},
        ];
    }

    get chartCardsRow1() {
        return this.chartCards.slice(0, 3);
    }

    get chartCardsRow2() {
        return this.chartCards.slice(3, 6);
    }

    get chartCardsRow3() {
        return this.chartCards.slice(6, 9);
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
            const response = await this.rpc("/purchase_request/dashboard/data", {
                fiscal_year_id: this.state.filters.fiscal_year_id,
                source_id: this.state.filters.source_id,
                selected_states: this.state.selectedStates,
            });

            this.state.filterOptions = response.filter_options;
            this.state.filters = response.filters;
            this.state.summaryBoxes = response.summary_boxes;
            this.state.chart1Data = response.chart1_purchase_type_by_month;
            this.state.chart2Data = response.chart2_purchase_type_pie;
            this.state.expensePieData = response.expense_type_pie;
            this.state.chart3Data = response.chart3_expense_type_by_month;
            this.state.chart4Data = response.chart4_approved_trend;
            this.state.chart5Data = response.chart5_purchase_type_by_dept;
            this.state.chart6Data = response.chart6_expense_type_by_dept;
            this.state.leadtimeHeatmap = response.chart7_leadtime_heatmap;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
            this._initCharts();
        }
    }

    _initCharts() {
        setTimeout(() => {
            this._updateChart1();
            this._updateChart2();
            this._updateChartExpensePie();
            this._updateChart3();
            this._updateChart4();
            this._updateChart5();
            this._updateChart6();
            this._updateChartLeadtime();
        }, 100);
    }

    _disposeCharts() {
        for (const prop of this._chartProps) {
            if (this[prop]) {
                this[prop].dispose();
                this[prop] = null;
            }
        }
    }

    /**
     * Get or create an ECharts instance for a given DOM element.
     *
     * OWL may re-render the DOM at any time, which orphans the old chart container.
     * We detect this by checking if the existing chart's DOM element is still in the
     * document. If not, we dispose the stale instance and create a new one.
     */
    _getOrCreateChart(propName, domId) {
        if (typeof echarts === "undefined") {
            return null;
        }
        const chartDom = document.getElementById(domId);
        if (!chartDom) {
            return null;
        }
        if (this[propName]) {
            const existingDom = this[propName].getDom();
            if (
                !existingDom ||
                !document.body.contains(existingDom) ||
                existingDom !== chartDom
            ) {
                this[propName].dispose();
                this[propName] = null;
            }
        }
        if (!this[propName]) {
            this[propName] = echarts.init(chartDom);
        }
        return this[propName];
    }

    // ──────────────────────────────────────────────────────────────────
    // Shared chart option builders
    // ──────────────────────────────────────────────────────────────────

    /**
     * Build a complete ECharts option for a stacked bar chart.
     * Used by Charts 1, 3, 5, 6 — the most common chart type in this dashboard.
     *
     * @param {Object} data - {series: [{name, data}]}
     * @param {Array} xData - X-axis category labels
     * @param {Object} xAxisOpts - Extra xAxis config (e.g., axisLabel rotation for dept charts)
     */
    _makeStackedBarOption(data, xData, xAxisOpts = {}) {
        const series = (data.series || []).map((s, i) => ({
            name: s.name,
            type: "bar",
            stack: "total",
            emphasis: {focus: "series"},
            data: s.data,
            itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
        }));

        return {
            tooltip: {
                trigger: "axis",
                axisPointer: {type: "shadow"},
                formatter: (params) => {
                    let result = `<strong>${params[0].axisValue}</strong><br/>`;
                    params.forEach((p) => {
                        if (p.value > 0) {
                            result += `${p.marker} ${p.seriesName}: ${this.formatCurrency(p.value)} บาท<br/>`;
                        }
                    });
                    return result;
                },
            },
            legend: {
                top: 0,
                type: "scroll",
            },
            grid: {
                left: "3%",
                right: "4%",
                bottom: "3%",
                top: 40,
                containLabel: true,
            },
            xAxis: {
                type: "category",
                data: xData,
                ...xAxisOpts,
            },
            yAxis: {
                type: "value",
                axisLabel: {
                    formatter: (val) => {
                        if (val >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
                        if (val >= 1e3) return `${(val / 1e3).toFixed(0)}K`;
                        return val;
                    },
                },
            },
            series: series,
        };
    }

    /**
     * Build ECharts option for a stacked area/line chart (Chart 4).
     * Reuses _makeStackedBarOption as a base and converts series to smooth lines.
     */
    _makeStackedLineOption(data, xData) {
        const option = this._makeStackedBarOption(data, xData);
        // Override to line-specific settings
        option.xAxis.boundaryGap = false;
        option.series = (data.series || []).map((s, i) => ({
            name: s.name,
            type: "line",
            stack: "total",
            smooth: true,
            emphasis: {focus: "series"},
            data: s.data,
            itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
        }));
        return option;
    }

    // ──────────────────────────────────────────────────────────────────
    // Individual chart update methods
    // ──────────────────────────────────────────────────────────────────

    // Chart 1: Stacked Bar — Procurement type by fiscal month
    _updateChart1() {
        const chart = this._getOrCreateChart("chart1", "prChart1");
        if (!chart) return;
        const data = this.state.chart1Data;
        chart.setOption(
            this._makeStackedBarOption(data, data.months || []),
            true
        );
    }

    // Chart 2: Doughnut — Procurement type breakdown (clickable → list view)
    _updateChart2() {
        const chart = this._getOrCreateChart("chart2", "prChart2");
        if (!chart) return;

        const pieData = (this.state.chart2Data || []).map((item, i) => ({
            ...item,
            itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
        }));

        chart.setOption(
            {
                tooltip: {
                    trigger: "item",
                    formatter: (params) =>
                        `${params.name}: ${this.formatCurrency(params.value)} บาท (${params.percent.toFixed(1)}%)`,
                },
                legend: {
                    orient: "vertical",
                    right: "5%",
                    top: "center",
                },
                series: [
                    {
                        name: "ประเภทการจัดซื้อจัดจ้าง",
                        type: "pie",
                        radius: ["40%", "70%"],
                        center: ["35%", "50%"],
                        avoidLabelOverlap: true,
                        itemStyle: {
                            borderRadius: 6,
                            borderColor: "#fff",
                            borderWidth: 2,
                        },
                        label: {
                            show: true,
                            formatter: (params) =>
                                params.percent < 5
                                    ? ""
                                    : `${params.percent.toFixed(0)}%`,
                            position: "inside",
                            fontSize: 11,
                            fontWeight: "bold",
                            color: "#fff",
                        },
                        emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowOffsetX: 0,
                                shadowColor: "rgba(0, 0, 0, 0.2)",
                            },
                        },
                        data: pieData,
                    },
                ],
            },
            true
        );

        // Click handler: navigate to list view filtered by all active dashboard filters.
        // Domain includes: procurement type (from slice), fiscal year, source (from control panel),
        // and state (from selected summary boxes, with "draft" mapping to include "to_examine").
        chart.off("click");
        chart.on("click", (params) => {
            const purchaseTypeId = params.data.procurement_type_id;
            if (purchaseTypeId) {
                const domain = [
                    ["procurement_type_id", "=", purchaseTypeId],
                    [
                        "account_fiscal_year_id",
                        "=",
                        this.state.filters.fiscal_year_id,
                    ],
                    [
                        "source_analytic_id",
                        "=",
                        this.state.filters.source_id,
                    ],
                ];
                const selected = this.state.selectedStates;
                if (selected.length > 0) {
                    const states = [...selected];
                    if (states.includes("draft")) {
                        states.push("to_examine");
                    }
                    domain.push(["state", "in", states]);
                } else {
                    domain.push(["state", "!=", "rejected"]);
                }
                this.action.doAction({
                    type: "ir.actions.act_window",
                    name: params.name,
                    res_model: "purchase.request",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                    domain: domain,
                    target: "current",
                });
            }
        });
    }

    // Expense Type Pie: Doughnut — Expense category breakdown (clickable → list view)
    _updateChartExpensePie() {
        const chart = this._getOrCreateChart("chartExpensePie", "prChartExpPie");
        if (!chart) return;

        const pieData = (this.state.expensePieData || []).map((item, i) => ({
            ...item,
            itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
        }));

        chart.setOption(
            {
                tooltip: {
                    trigger: "item",
                    formatter: (params) =>
                        `${params.name}: ${this.formatCurrency(params.value)} บาท (${params.percent.toFixed(1)}%)`,
                },
                legend: {
                    orient: "vertical",
                    right: "5%",
                    top: "center",
                },
                series: [
                    {
                        name: "ประเภทค่าใช้จ่าย",
                        type: "pie",
                        radius: ["40%", "70%"],
                        center: ["35%", "50%"],
                        avoidLabelOverlap: true,
                        itemStyle: {
                            borderRadius: 6,
                            borderColor: "#fff",
                            borderWidth: 2,
                        },
                        label: {
                            show: true,
                            formatter: (params) =>
                                params.percent < 5
                                    ? ""
                                    : `${params.percent.toFixed(0)}%`,
                            position: "inside",
                            fontSize: 11,
                            fontWeight: "bold",
                            color: "#fff",
                        },
                        emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowOffsetX: 0,
                                shadowColor: "rgba(0, 0, 0, 0.2)",
                            },
                        },
                        data: pieData,
                    },
                ],
            },
            true
        );

        // Click handler: navigate to list view filtered by budget accounts in this category
        chart.off("click");
        chart.on("click", (params) => {
            const accountIds = params.data.budget_account_ids;
            if (accountIds && accountIds.length) {
                const domain = [
                    ["budget_account_id", "in", accountIds],
                    [
                        "account_fiscal_year_id",
                        "=",
                        this.state.filters.fiscal_year_id,
                    ],
                    [
                        "source_analytic_id",
                        "=",
                        this.state.filters.source_id,
                    ],
                ];
                const selected = this.state.selectedStates;
                if (selected.length > 0) {
                    const states = [...selected];
                    if (states.includes("draft")) {
                        states.push("to_examine");
                    }
                    domain.push(["state", "in", states]);
                } else {
                    domain.push(["state", "!=", "rejected"]);
                }
                this.action.doAction({
                    type: "ir.actions.act_window",
                    name: params.name,
                    res_model: "purchase.request",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                    domain: domain,
                    target: "current",
                });
            }
        });
    }

    // Chart 3: Stacked Bar — Expense category by fiscal month
    _updateChart3() {
        const chart = this._getOrCreateChart("chart3", "prChart3");
        if (!chart) return;
        const data = this.state.chart3Data;
        chart.setOption(
            this._makeStackedBarOption(data, data.months || []),
            true
        );
    }

    // Chart 4: Stacked Line — Approval trend by procurement type (date_approved)
    _updateChart4() {
        const chart = this._getOrCreateChart("chart4", "prChart4");
        if (!chart) return;
        const data = this.state.chart4Data;
        chart.setOption(
            this._makeStackedLineOption(data, data.months || []),
            true
        );
    }

    // Chart 5: Stacked Bar — Procurement type by department
    _updateChart5() {
        const chart = this._getOrCreateChart("chart5", "prChart5");
        if (!chart) return;
        const data = this.state.chart5Data;
        const deptAxisOpts = {
            axisLabel: {rotate: 30, overflow: "truncate", width: 80},
        };
        chart.setOption(
            this._makeStackedBarOption(data, data.departments || [], deptAxisOpts),
            true
        );
    }

    // Chart 6: Stacked Bar — Expense category by department
    _updateChart6() {
        const chart = this._getOrCreateChart("chart6", "prChart6");
        if (!chart) return;
        const data = this.state.chart6Data;
        const deptAxisOpts = {
            axisLabel: {rotate: 30, overflow: "truncate", width: 80},
        };
        chart.setOption(
            this._makeStackedBarOption(data, data.departments || [], deptAxisOpts),
            true
        );
    }

    // Chart 7: Stock Heatmap
    _updateChartLeadtime() {
        const chart = this._getOrCreateChart("chartLeadtime", "prChartLeadtime");
        if (!chart) return;

        const raw = this.state.leadtimeHeatmap || [];
        if (!raw.length) return;

        // ใช้ avg สำหรับ normalize สี และขนาด block
        const maxVal = Math.max(...raw.map((d) => d.avg), 1);

        const treemapData = raw.map((item) => ({
            name: item.name,
            value: Math.max(item.avg, 0.1),  // ขนาด block ตาม avg
            itemStyle: {
                color: item.avg === 0
                    ? "#d9d9d9"
                    : this._durationToColor(item.avg, maxVal),
            },
            _avg: item.avg,
            _total: item.total,
            _count: item.count,
        }));

        chart.setOption({
            tooltip: {
                formatter: (params) => {
                    const d = params.data;
                    if (d._avg === 0) {
                        return `<strong>${d.name}</strong><br/>ยังไม่มีข้อมูล`;
                    }
                    return `
                        <strong>${d.name}</strong><br/>
                        ระยะเวลาเฉลี่ย: ${this._formatDuration(d._avg)}<br/>
                        ระยะเวลาสะสม: ${this._formatDuration(d._total)}<br/>
                    `;
                },
            },
            series: [{
                name: "Leadtime",
                type: "treemap",
                roam: false,
                nodeClick: false,
                breadcrumb: {show: false},
                width: "100%",
                height: "100%",
                label: {
                    show: true,
                    formatter: (params) => {
                        const d = params.data;
                        if (d._avg === 0) {
                            return `{name|${d.name}}\n{sub|ยังไม่มีข้อมูล}`;
                        }
                        // แสดง avg ใน block
                        return `{name|${d.name}}\n{sub|${this._formatDuration(d._avg)}}`;
                    },
                    rich: {
                        name: {fontSize: 13, fontWeight: "bold", color: "#fff", lineHeight: 20},
                        sub: {fontSize: 12, color: "rgba(255,255,255,0.85)", lineHeight: 18},
                    },
                },
                itemStyle: {
                    borderWidth: 4,
                    borderColor: "#fff",
                    gapWidth: 4,
                },
                data: treemapData,
            }],
        }, true);
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
        if (amount === null || amount === undefined) {
            return "0.00";
        }
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(amount);
    }

    formatNumber(num) {
        if (num === null || num === undefined) {
            return "0";
        }
        return new Intl.NumberFormat("th-TH").format(num);
    }

    getBoxColorClass(state) {
        const classes = {
            draft: "text-dark",
            to_verify: "text-info",
            to_approve: "text-warning",
            approved: "text-success",
            in_progress: "text-primary",
            done: "text-success",
            rejected: "text-danger",
            total: "text-primary",
        };
        return classes[state] || "text-secondary";
    }

    _durationToColor(value, maxVal) {
        const ratio = Math.min(value / maxVal, 1);
        // ratio 0 = เขียว (#3ba272), ratio 1 = แดง (#ee6666)
        const r = Math.round(59 + (238 - 59) * ratio);
        const g = Math.round(162 + (102 - 162) * ratio);
        const b = Math.round(114 + (102 - 114) * ratio);
        return `rgb(${r},${g},${b})`;
    }

    _formatDuration(minutes) {
        if (minutes < 60) {
            return `${minutes.toFixed(2)} นาที`;
        } else if (minutes < 60 * 24) {
            return `${(minutes / 60).toFixed(2)} ชั่วโมง`;
        } else {
            return `${(minutes / 60 / 24).toFixed(2)} วัน`;
        }
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
