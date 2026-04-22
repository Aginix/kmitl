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
            chart3Data: {months: [], series: []},
            chart4Data: {months: [], series: []},
            chart5Data: {departments: [], series: []},
            chart6Data: {departments: [], series: []},
            filterOptions: {
                fiscal_years: [],
                sources: [],
            },
        });

        this.chart1 = null;
        this.chart2 = null;
        this.chart3 = null;
        this.chart4 = null;
        this.chart5 = null;
        this.chart6 = null;

        this._onResize = () => {
            for (let i = 1; i <= 6; i++) {
                if (this[`chart${i}`]) this[`chart${i}`].resize();
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
            this.state.chart3Data = response.chart3_expense_type_by_month;
            this.state.chart4Data = response.chart4_approved_trend;
            this.state.chart5Data = response.chart5_purchase_type_by_dept;
            this.state.chart6Data = response.chart6_expense_type_by_dept;
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
            this._updateChart3();
            this._updateChart4();
            this._updateChart5();
            this._updateChart6();
        }, 100);
    }

    _disposeCharts() {
        for (let i = 1; i <= 6; i++) {
            if (this[`chart${i}`]) {
                this[`chart${i}`].dispose();
                this[`chart${i}`] = null;
            }
        }
    }

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

    _makeStackedBarOption(data, xField, xData) {
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

    // Chart 1: Stacked Bar - Purchase Type by Month
    _updateChart1() {
        const chart = this._getOrCreateChart("chart1", "prChart1");
        if (!chart) return;

        const data = this.state.chart1Data;
        chart.setOption(this._makeStackedBarOption(data, "months", data.months || []), true);
    }

    // Chart 2: Pie - Purchase Type (clickable)
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

        // Click handler → navigate to tree view
        chart.off("click");
        chart.on("click", (params) => {
            const purchaseTypeId = params.data.procurement_type_id;
            if (purchaseTypeId) {
                this.action.doAction({
                    type: "ir.actions.act_window",
                    name: params.name,
                    res_model: "purchase.request",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                    domain: [
                        ["procurement_type_id", "=", purchaseTypeId],
                        [
                            "account_fiscal_year_id",
                            "=",
                            this.state.filters.fiscal_year_id,
                        ],
                    ],
                    target: "current",
                });
            }
        });
    }

    // Chart 3: Stacked Bar - Expense Type by Month
    _updateChart3() {
        const chart = this._getOrCreateChart("chart3", "prChart3");
        if (!chart) return;

        const data = this.state.chart3Data;
        chart.setOption(this._makeStackedBarOption(data, "months", data.months || []), true);
    }

    // Chart 4: Stacked Line - Approved Trend
    _updateChart4() {
        const chart = this._getOrCreateChart("chart4", "prChart4");
        if (!chart) return;

        const data = this.state.chart4Data;
        const series = (data.series || []).map((s, i) => ({
            name: s.name,
            type: "line",
            stack: "total",
            smooth: true,
            areaStyle: {opacity: 0.3},
            emphasis: {focus: "series"},
            data: s.data,
            itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
        }));

        chart.setOption(
            {
                tooltip: {
                    trigger: "axis",
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
                    boundaryGap: false,
                    data: data.months || [],
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
            },
            true
        );
    }

    // Chart 5: Stacked Bar - Purchase Type by Department
    _updateChart5() {
        const chart = this._getOrCreateChart("chart5", "prChart5");
        if (!chart) return;

        const data = this.state.chart5Data;
        const series = (data.series || []).map((s, i) => ({
            name: s.name,
            type: "bar",
            stack: "total",
            emphasis: {focus: "series"},
            data: s.data,
            itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
        }));

        chart.setOption(
            {
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
                    data: data.departments || [],
                    axisLabel: {
                        rotate: 30,
                        overflow: "truncate",
                        width: 80,
                    },
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
            },
            true
        );
    }

    // Chart 6: Stacked Bar - Expense Type by Department
    _updateChart6() {
        const chart = this._getOrCreateChart("chart6", "prChart6");
        if (!chart) return;

        const data = this.state.chart6Data;
        const series = (data.series || []).map((s, i) => ({
            name: s.name,
            type: "bar",
            stack: "total",
            emphasis: {focus: "series"},
            data: s.data,
            itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
        }));

        chart.setOption(
            {
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
                    data: data.departments || [],
                    axisLabel: {
                        rotate: 30,
                        overflow: "truncate",
                        width: 80,
                    },
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
            },
            true
        );
    }

    // Event handlers
    onFiscalYearChange(ev) {
        const value = ev.target.value;
        this.state.filters.fiscal_year_id = value ? parseInt(value, 10) : null;
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

    onSourceChange(ev) {
        const value = ev.target.value;
        this.state.filters.source_id = value ? parseInt(value, 10) : null;
        this.loadData();
    }

    // Helpers
    isFiscalYearSelected(fyId) {
        return String(fyId) === String(this.state.filters.fiscal_year_id);
    }

    isSourceSelected(srcId) {
        return String(srcId) === String(this.state.filters.source_id);
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
}

PurchaseRequestDashboard.template =
    "purchase_request_dashboard.PurchaseRequestDashboard";
PurchaseRequestDashboard.components = {
    ControlPanel,
};

registry
    .category("actions")
    .add("purchase_request_dashboard", PurchaseRequestDashboard);
