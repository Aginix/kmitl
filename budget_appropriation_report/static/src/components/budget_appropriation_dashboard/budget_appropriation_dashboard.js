/** @odoo-module **/

import {Component, onMounted, onWillStart, onWillUnmount, useState} from "@odoo/owl";

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class BudgetAppropriationDashboard extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false,
        };

        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.state = useState({
            filters: {
                fiscal_year_id: null,
                source_id: null,
            },
            loading: false,
            activeTab: "overview",
            stats: {
                report_count: 0,
                department_count: 0,
                total_revenue: 0,
                total_expense: 0,
                pie_chart: [],
            },
            fiscalYear: null,
            filterOptions: {
                fiscal_years: [],
                sources: [],
            },
        });

        this.chart = null;
        this.treemapChart = null;
        this.revenueTreemapChart = null;
        this.deptAccountChart = null;
        this.accountOnlyChart = null;

        onWillStart(async () => {
            await this._loadECharts();
            await this.loadData();
        });

        onMounted(() => {
            this._initCharts();
        });

        onWillUnmount(() => {
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

    _initCharts() {
        setTimeout(() => {
            const activeTab = this.state.activeTab;
            if (activeTab === "overview") {
                this._updateChart();
            } else if (activeTab === "revenue") {
                this._updateRevenueTreeMap();
            } else if (activeTab === "expense") {
                this._updateTreeMap();
            } else if (activeTab === "dept-account") {
                this._updateDeptAccountTreeMap();
            } else if (activeTab === "account-only") {
                this._updateAccountOnlyTreeMap();
            }
        }, 100);
    }

    _updateChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("budgetPieChart");
        if (!chartDom) {
            return;
        }

        if (!this.chart) {
            this.chart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.chart) {
                    this.chart.resize();
                }
            });
        }

        const pieData = this.state.stats.pie_chart || [];

        const option = {
            tooltip: {
                trigger: "item",
                formatter: (params) => {
                    const value = this.formatCurrency(params.value);
                    return `${params.name}: ${value} บาท (${params.percent.toFixed(1)}%)`;
                },
            },
            legend: {
                orient: "horizontal",
                bottom: "0%",
                left: "center",
            },
            color: ["#28a745", "#dc3545"],
            series: [
                {
                    name: "งบประมาณ",
                    type: "pie",
                    radius: ["45%", "75%"],
                    center: ["50%", "45%"],
                    avoidLabelOverlap: true,
                    itemStyle: {
                        borderRadius: 6,
                        borderColor: "#fff",
                        borderWidth: 2,
                    },
                    label: {
                        show: true,
                        formatter: (params) => {
                            if (params.value === 0) return "";
                            return `${params.percent.toFixed(1)}%`;
                        },
                        position: "inside",
                        fontSize: 14,
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
        };

        this.chart.setOption(option, true);
    }

    _updateTreeMap() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("budgetTreeMap");
        if (!chartDom) {
            return;
        }

        if (!this.treemapChart) {
            this.treemapChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.treemapChart) {
                    this.treemapChart.resize();
                }
            });
        }

        const treemapData = this.state.stats.treemap_data || [];

        const option = {
            tooltip: {
                formatter: (params) => {
                    const value = this.formatCurrency(params.value);
                    return `${params.name}<br/>งบประมาณ: ${value} บาท`;
                },
            },
            series: [
                {
                    type: "treemap",
                    roam: false,
                    nodeClick: false,
                    breadcrumb: {show: false},
                    label: {
                        show: true,
                        formatter: "{b}",
                        fontSize: 12,
                    },
                    itemStyle: {
                        borderColor: "#fff",
                        borderWidth: 2,
                        gapWidth: 2,
                    },
                    levels: [
                        {
                            itemStyle: {
                                borderColor: "#fff",
                                borderWidth: 2,
                                gapWidth: 2,
                            },
                            colorSaturation: [0.3, 0.6],
                        },
                    ],
                    data: treemapData,
                },
            ],
        };

        this.treemapChart.setOption(option, true);
    }

    _updateRevenueTreeMap() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("revenueTreeMap");
        if (!chartDom) {
            return;
        }

        if (!this.revenueTreemapChart) {
            this.revenueTreemapChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.revenueTreemapChart) {
                    this.revenueTreemapChart.resize();
                }
            });
        }

        const treemapData = this.state.stats.revenue_treemap_data || [];

        const option = {
            tooltip: {
                formatter: (params) => {
                    const value = this.formatCurrency(params.value);
                    return `${params.name}<br/>ประมาณการรายรับ: ${value} บาท`;
                },
            },
            series: [
                {
                    type: "treemap",
                    roam: false,
                    nodeClick: false,
                    breadcrumb: {show: false},
                    label: {
                        show: true,
                        formatter: (params) => {
                            const value = this.formatCurrency(params.value);
                            return `${params.name}\n${value} บาท`;
                        },
                        fontSize: 12,
                    },
                    itemStyle: {
                        borderColor: "#fff",
                        borderWidth: 2,
                        gapWidth: 2,
                    },
                    levels: [
                        {
                            itemStyle: {
                                borderColor: "#fff",
                                borderWidth: 2,
                                gapWidth: 2,
                            },
                            colorSaturation: [0.3, 0.6],
                        },
                    ],
                    color: ["#28a745", "#20c997", "#17a2b8", "#6f42c1"],
                    data: treemapData,
                },
            ],
        };

        this.revenueTreemapChart.setOption(option, true);
    }

    _updateDeptAccountTreeMap() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("budgetDeptAccountTreeMap");
        if (!chartDom) {
            return;
        }

        if (!this.deptAccountChart) {
            this.deptAccountChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.deptAccountChart) {
                    this.deptAccountChart.resize();
                }
            });
        }

        const data = this.state.stats.department_account_treemap || [];

        const option = {
            tooltip: {
                formatter: (params) => {
                    const value = this.formatCurrency(params.value);
                    return `${params.name}<br/>งบประมาณ: ${value} บาท`;
                },
            },
            series: [
                {
                    type: "treemap",
                    roam: true,
                    nodeClick: "zoomToNode",
                    breadcrumb: {
                        show: true,
                        itemStyle: {color: "#6c757d"},
                        emphasis: {itemStyle: {color: "#495057"}},
                    },
                    label: {
                        show: true,
                        formatter: (params) => {
                            const value = this.formatCurrency(params.value);
                            return `${params.name}\n${value} บาท`;
                        },
                        fontSize: 12,
                    },
                    upperLabel: {
                        show: true,
                        height: 30,
                        formatter: (params) => {
                            const value = this.formatCurrency(params.value);
                            return `${params.name}: ${value} บาท`;
                        },
                    },
                    itemStyle: {
                        borderColor: "#fff",
                        borderWidth: 2,
                        gapWidth: 2,
                    },
                    levels: [
                        {
                            itemStyle: {
                                borderColor: "#111",
                                borderWidth: 0,
                                gapWidth: 1,
                            },
                            upperLabel: {
                                show: false,
                            },
                        },
                        {
                            itemStyle: {
                                borderColor: "#555",
                                borderWidth: 5,
                                gapWidth: 1,
                            },
                            emphasis: {
                                itemStyle: {
                                    borderColor: "#ddd",
                                },
                            },
                        },
                        {
                            colorSaturation: [0.35, 0.5],
                            itemStyle: {
                                borderWidth: 5,
                                gapWidth: 1,
                                borderColorSaturation: 0.6,
                            },
                        },
                    ],
                    data: data,
                },
            ],
        };

        this.deptAccountChart.setOption(option, true);
    }

    _updateAccountOnlyTreeMap() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("budgetAccountOnlyTreeMap");
        if (!chartDom) {
            return;
        }

        if (!this.accountOnlyChart) {
            this.accountOnlyChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.accountOnlyChart) {
                    this.accountOnlyChart.resize();
                }
            });
        }

        const data = this.state.stats.account_only_treemap || [];

        const option = {
            tooltip: {
                formatter: (params) => {
                    const value = this.formatCurrency(params.value);
                    return `${params.name}<br/>งบประมาณ: ${value} บาท`;
                },
            },
            series: [
                {
                    type: "treemap",
                    roam: true,
                    nodeClick: "zoomToNode",
                    breadcrumb: {
                        show: true,
                        itemStyle: {color: "#6c757d"},
                        emphasis: {itemStyle: {color: "#495057"}},
                    },
                    label: {
                        show: true,
                        formatter: (params) => {
                            const value = this.formatCurrency(params.value);
                            return `${params.name}\n${value} บาท`;
                        },
                        fontSize: 12,
                    },
                    upperLabel: {
                        show: true,
                        height: 30,
                        formatter: (params) => {
                            const value = this.formatCurrency(params.value);
                            return `${params.name}: ${value} บาท`;
                        },
                    },
                    itemStyle: {
                        borderColor: "#fff",
                        borderWidth: 2,
                        gapWidth: 2,
                    },
                    levels: [
                        {
                            itemStyle: {
                                borderColor: "#e27500",
                                borderWidth: 0,
                                gapWidth: 1,
                            },
                            upperLabel: {
                                show: false,
                            },
                        },
                        {
                            itemStyle: {
                                borderColor: "#555",
                                borderWidth: 5,
                                gapWidth: 1,
                            },
                            emphasis: {
                                itemStyle: {
                                    borderColor: "#ddd",
                                },
                            },
                        },
                        {
                            colorSaturation: [0.35, 0.5],
                            itemStyle: {
                                borderWidth: 5,
                                gapWidth: 1,
                                borderColorSaturation: 0.6,
                            },
                        },
                    ],
                    // levels: [
                    //     {
                    //         // Level 0: Root Budget Accounts (งบบุคลากร, งบดำเนินงาน, etc.)
                    //         itemStyle: {
                    //             borderColor: "#fff",
                    //             borderWidth: 4,
                    //             gapWidth: 4,
                    //         },
                    //         upperLabel: {show: true, height: 30},
                    //         colorSaturation: [0.3, 0.45],
                    //     },
                    //     {
                    //         // Level 1: Child accounts
                    //         itemStyle: {
                    //             borderColor: "#fff",
                    //             borderWidth: 3,
                    //             gapWidth: 3,
                    //         },
                    //         upperLabel: {show: true, height: 26},
                    //         colorSaturation: [0.4, 0.55],
                    //     },
                    //     {
                    //         // Level 2: Grandchild accounts
                    //         itemStyle: {
                    //             borderColor: "#fff",
                    //             borderWidth: 2,
                    //             gapWidth: 2,
                    //         },
                    //         upperLabel: {show: true, height: 22},
                    //         colorSaturation: [0.5, 0.65],
                    //     },
                    //     {
                    //         // Level 3+: Deeper levels
                    //         itemStyle: {
                    //             borderColor: "#fff",
                    //             borderWidth: 1,
                    //             gapWidth: 1,
                    //         },
                    //         colorSaturation: [0.6, 0.8],
                    //     },
                    // ],
                    data: data,
                },
            ],
        };

        this.accountOnlyChart.setOption(option, true);
    }

    _disposeCharts() {
        if (this.chart) {
            this.chart.dispose();
            this.chart = null;
        }
        if (this.treemapChart) {
            this.treemapChart.dispose();
            this.treemapChart = null;
        }
        if (this.revenueTreemapChart) {
            this.revenueTreemapChart.dispose();
            this.revenueTreemapChart = null;
        }
        if (this.deptAccountChart) {
            this.deptAccountChart.dispose();
            this.deptAccountChart = null;
        }
        if (this.accountOnlyChart) {
            this.accountOnlyChart.dispose();
            this.accountOnlyChart = null;
        }
    }

    async loadData() {
        this._disposeCharts();
        this.state.loading = true;
        try {
            const response = await this.rpc("/budget_appropriation/dashboard/data", {
                fiscal_year_id: this.state.filters.fiscal_year_id,
                source_id: this.state.filters.source_id,
            });

            this.state.filterOptions = response.filter_options;
            this.state.filters = response.filters;
            this.state.fiscalYear = response.fiscal_year;
            this.state.stats = response.stats;
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล: " + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
            this._initCharts();
        }
    }

    async onFiscalYearChange(e) {
        const fiscalYearId = e.target.value ? Number(e.target.value) : null;
        this.state.filters.fiscal_year_id = fiscalYearId;
        await this.loadData();
    }

    async onSourceChange(e) {
        const sourceId = e.target.value ? Number(e.target.value) : null;
        this.state.filters.source_id = sourceId;
        await this.loadData();
    }

    isFiscalYearSelected(fyId) {
        return fyId === this.state.filters.fiscal_year_id;
    }

    isSourceSelected(sourceId) {
        return sourceId === this.state.filters.source_id;
    }

    onTabChange(tabId) {
        // Dispose all charts before switching tabs (DOM elements will be recreated)
        this._disposeCharts();
        this.state.activeTab = tabId;
        // Re-initialize chart for the active tab after DOM updates
        setTimeout(() => {
            if (tabId === "overview") {
                this._updateChart();
            } else if (tabId === "revenue") {
                this._updateRevenueTreeMap();
            } else if (tabId === "expense") {
                this._updateTreeMap();
            } else if (tabId === "dept-account") {
                this._updateDeptAccountTreeMap();
            } else if (tabId === "account-only") {
                this._updateAccountOnlyTreeMap();
            }
        }, 100);
    }

    isTabActive(tabId) {
        return this.state.activeTab === tabId;
    }

    get selectedFiscalYear() {
        return this.state.fiscalYear ? this.state.fiscalYear.name : "";
    }

    formatCurrency(amount) {
        if (amount === null || amount === undefined) {
            return "0";
        }
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    }
}

BudgetAppropriationDashboard.template =
    "budget_appropriation_report.BudgetAppropriationDashboard";
BudgetAppropriationDashboard.components = {
    ControlPanel,
};

registry
    .category("actions")
    .add("budget_appropriation_dashboard", BudgetAppropriationDashboard);
