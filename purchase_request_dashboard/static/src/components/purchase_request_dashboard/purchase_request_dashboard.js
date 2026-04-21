/** @odoo-module **/

import {Component, onMounted, onWillStart, onWillUnmount, useState} from "@odoo/owl";

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

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
                department_id: null,
                source_id: null,
            },
            loading: false,
            stats: {
                total_count: 0,
                total_amount: 0,
                pending_approval_count: 0,
                approved_count: 0,
                in_progress_count: 0,
                rejected_count: 0,
                state_pie_data: [],
                dept_bar_data: {departments: [], series: []},
                fy_bar_data: {fiscal_years: [], series: []},
                trend_line_data: {months: [], series: []},
                table_data: [],
            },
            filterOptions: {
                fiscal_years: [],
                departments: [],
                sources: [],
            },
        });

        this.statePieChart = null;
        this.deptBarChart = null;
        this.fyBarChart = null;
        this.trendLineChart = null;

        this._onResize = () => {
            if (this.statePieChart) this.statePieChart.resize();
            if (this.deptBarChart) this.deptBarChart.resize();
            if (this.fyBarChart) this.fyBarChart.resize();
            if (this.trendLineChart) this.trendLineChart.resize();
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
                department_id: this.state.filters.department_id,
                source_id: this.state.filters.source_id,
            });

            this.state.filterOptions = response.filter_options;
            this.state.filters = response.filters;
            this.state.stats = response.stats;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
            this._initCharts();
        }
    }

    _initCharts() {
        setTimeout(() => {
            this._updateStatePieChart();
            this._updateDeptBarChart();
            this._updateFyBarChart();
            this._updateTrendLineChart();
        }, 100);
    }

    _disposeCharts() {
        const charts = [
            "statePieChart",
            "deptBarChart",
            "fyBarChart",
            "trendLineChart",
        ];
        for (const name of charts) {
            if (this[name]) {
                this[name].dispose();
                this[name] = null;
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

    _updateStatePieChart() {
        const chart = this._getOrCreateChart("statePieChart", "prStatePieChart");
        if (!chart) return;

        const pieData = this.state.stats.state_pie_data || [];
        chart.setOption(
            {
                tooltip: {
                    trigger: "item",
                    formatter: (params) =>
                        `${params.name}: ${params.value} รายการ (${params.percent.toFixed(1)}%)`,
                },
                legend: {
                    orient: "vertical",
                    right: "5%",
                    top: "center",
                },
                series: [
                    {
                        name: "สถานะ",
                        type: "pie",
                        radius: ["45%", "75%"],
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
                                params.value === 0
                                    ? ""
                                    : `${params.percent.toFixed(0)}%`,
                            position: "inside",
                            fontSize: 12,
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
    }

    _updateDeptBarChart() {
        const chart = this._getOrCreateChart("deptBarChart", "prDeptBarChart");
        if (!chart) return;

        const data = this.state.stats.dept_bar_data || {
            departments: [],
            series: [],
        };
        const series = (data.series || []).map((s) => ({
            name: s.name,
            type: "bar",
            stack: "total",
            emphasis: {focus: "series"},
            data: s.data,
            itemStyle: {color: s.color},
        }));

        chart.setOption(
            {
                tooltip: {
                    trigger: "axis",
                    axisPointer: {type: "shadow"},
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
                xAxis: {type: "value"},
                yAxis: {
                    type: "category",
                    data: data.departments || [],
                    axisLabel: {
                        width: 120,
                        overflow: "truncate",
                    },
                },
                series: series,
            },
            true
        );
    }

    _updateFyBarChart() {
        const chart = this._getOrCreateChart("fyBarChart", "prFyBarChart");
        if (!chart) return;

        const data = this.state.stats.fy_bar_data || {
            fiscal_years: [],
            series: [],
        };
        const series = (data.series || []).map((s) => ({
            name: s.name,
            type: "bar",
            stack: "total",
            emphasis: {focus: "series"},
            data: s.data,
            itemStyle: {color: s.color},
        }));

        chart.setOption(
            {
                tooltip: {
                    trigger: "axis",
                    axisPointer: {type: "shadow"},
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
                    data: data.fiscal_years || [],
                },
                yAxis: {type: "value"},
                series: series,
            },
            true
        );
    }

    _updateTrendLineChart() {
        const chart = this._getOrCreateChart(
            "trendLineChart",
            "prTrendLineChart"
        );
        if (!chart) return;

        const data = this.state.stats.trend_line_data || {
            months: [],
            series: [],
        };
        const series = (data.series || []).map((s) => ({
            name: s.name,
            type: "line",
            smooth: true,
            data: s.data,
            emphasis: {focus: "series"},
        }));

        chart.setOption(
            {
                tooltip: {
                    trigger: "axis",
                },
                legend: {
                    top: 0,
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
                yAxis: {type: "value"},
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

    onDepartmentChange(ev) {
        const value = ev.target.value;
        this.state.filters.department_id = value ? parseInt(value, 10) : null;
        this.loadData();
    }

    onSourceChange(ev) {
        const value = ev.target.value;
        this.state.filters.source_id = value ? parseInt(value, 10) : null;
        this.loadData();
    }

    onRowClick(requestId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "purchase.request",
            res_id: requestId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // Helpers
    isFiscalYearSelected(fyId) {
        return String(fyId) === String(this.state.filters.fiscal_year_id);
    }

    isDepartmentSelected(deptId) {
        return String(deptId) === String(this.state.filters.department_id);
    }

    isSourceSelected(srcId) {
        return String(srcId) === String(this.state.filters.source_id);
    }

    formatCurrency(amount) {
        if (amount === null || amount === undefined) {
            return "0";
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

    getStateClass(state) {
        const classes = {
            draft: "badge bg-secondary",
            to_examine: "badge bg-info",
            to_verify: "badge bg-info",
            to_approve: "badge bg-warning",
            approved: "badge bg-success",
            in_progress: "badge bg-primary",
            done: "badge bg-success",
            rejected: "badge bg-danger",
        };
        return classes[state] || "badge bg-secondary";
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
