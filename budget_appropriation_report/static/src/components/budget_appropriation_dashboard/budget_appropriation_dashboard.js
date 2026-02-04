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
        this.activityTreemapChart = null;
        this.fundTreemapChart = null;
        this.sunburstChart = null;
        this.sankeyChart = null;
        this.heatmapChart = null;
        this.fundPieChart = null;
        this.accountTypePieChart = null;
        this.departmentPieChart = null;
        this.stackedBarChart = null;
        this.activitySankeyChart = null;

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
            } else if (activeTab === "expense-activity") {
                this._updateActivityTreeMap();
            } else if (activeTab === "expense-fund") {
                this._updateFundTreeMap();
            } else if (activeTab === "dept-account") {
                this._updateDeptAccountTreeMap();
            } else if (activeTab === "account-only") {
                this._updateAccountOnlyTreeMap();
            } else if (activeTab === "sunburst") {
                this._updateSunburstChart();
            } else if (activeTab === "sankey") {
                this._updateSankeyChart();
            } else if (activeTab === "heatmap") {
                this._updateHeatmapChart();
            } else if (activeTab === "executive") {
                this._updateFundPieChart();
                this._updateAccountTypePieChart();
                this._updateDepartmentPieChart();
                this._updateStackedBarChart();
                this._updateActivitySankeyChart();
            }
            // "table" tab doesn't need chart initialization
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

    _updateActivityTreeMap() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("activityTreeMap");
        if (!chartDom) {
            return;
        }

        if (!this.activityTreemapChart) {
            this.activityTreemapChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.activityTreemapChart) {
                    this.activityTreemapChart.resize();
                }
            });
        }

        const data = this.state.stats.activity_treemap || [];

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
                                borderColor: "#0d6efd",
                                borderWidth: 0,
                                gapWidth: 1,
                            },
                            upperLabel: {show: false},
                        },
                        {
                            itemStyle: {
                                borderColor: "#555",
                                borderWidth: 5,
                                gapWidth: 1,
                            },
                            emphasis: {itemStyle: {borderColor: "#ddd"}},
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
                    color: ["#0d6efd", "#6610f2", "#6f42c1", "#d63384", "#dc3545"],
                    data: data,
                },
            ],
        };

        this.activityTreemapChart.setOption(option, true);
    }

    _updateFundTreeMap() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("fundTreeMap");
        if (!chartDom) {
            return;
        }

        if (!this.fundTreemapChart) {
            this.fundTreemapChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.fundTreemapChart) {
                    this.fundTreemapChart.resize();
                }
            });
        }

        const data = this.state.stats.fund_treemap || [];

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
                                borderColor: "#198754",
                                borderWidth: 0,
                                gapWidth: 1,
                            },
                            upperLabel: {show: false},
                        },
                        {
                            itemStyle: {
                                borderColor: "#555",
                                borderWidth: 5,
                                gapWidth: 1,
                            },
                            emphasis: {itemStyle: {borderColor: "#ddd"}},
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
                    color: ["#198754", "#20c997", "#0dcaf0", "#ffc107", "#fd7e14"],
                    data: data,
                },
            ],
        };

        this.fundTreemapChart.setOption(option, true);
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
            title: {
                text: "งบประมาณรายจ่ายตามประเภทงบ",
                subtext: '(คลิกเพื่อดูรายละเอียดประเภทงบย่อย)',
                left: "center",
                top: 10,
                textStyle: {
                    fontSize: 14,
                    fontWeight: "bold",
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

    _updateSunburstChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("sunburstChart");
        if (!chartDom) {
            return;
        }

        if (!this.sunburstChart) {
            this.sunburstChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.sunburstChart) {
                    this.sunburstChart.resize();
                }
            });
        }

        const data = this.state.stats.sunburst_data || [];

        const option = {
            tooltip: {
                formatter: (params) => {
                    if (params.value) {
                        const value = this.formatCurrency(params.value);
                        return `${params.name}<br/>งบประมาณ: ${value} บาท`;
                    }
                    return params.name;
                },
            },
            series: [
                {
                    type: "sunburst",
                    data: data,
                    radius: [60, "90%"],
                    itemStyle: {
                        borderRadius: 4,
                        borderWidth: 2,
                    },
                    label: {
                        rotate: "radial",
                        fontSize: 10,
                    },
                    levels: [
                        {},
                        {
                            r0: "15%",
                            r: "45%",
                            itemStyle: {borderWidth: 2},
                            label: {rotate: "tangential", fontSize: 11},
                        },
                        {
                            r0: "45%",
                            r: "70%",
                            label: {align: "right", fontSize: 9},
                        },
                        {
                            r0: "70%",
                            r: "90%",
                            label: {
                                position: "outside",
                                padding: 3,
                                silent: false,
                                fontSize: 8,
                            },
                            itemStyle: {borderWidth: 1},
                        },
                    ],
                },
            ],
        };

        this.sunburstChart.setOption(option, true);
    }

    _updateSankeyChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("sankeyChart");
        if (!chartDom) {
            return;
        }

        if (!this.sankeyChart) {
            this.sankeyChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.sankeyChart) {
                    this.sankeyChart.resize();
                }
            });
        }

        const sankeyData = this.state.stats.sankey_data || {nodes: [], links: []};

        const option = {
            tooltip: {
                trigger: "item",
                triggerOn: "mousemove",
                formatter: (params) => {
                    if (params.dataType === "edge") {
                        const value = this.formatCurrency(params.value);
                        return `${params.data.source} → ${params.data.target}<br/>งบประมาณ: ${value} บาท`;
                    }
                    return params.name;
                },
            },
            series: [
                {
                    type: "sankey",
                    data: sankeyData.nodes,
                    links: sankeyData.links,
                    emphasis: {focus: "adjacency"},
                    lineStyle: {
                        color: "gradient",
                        curveness: 0.5,
                    },
                    label: {
                        fontSize: 10,
                    },
                    nodeWidth: 20,
                    nodeGap: 12,
                    layoutIterations: 32,
                },
            ],
        };

        this.sankeyChart.setOption(option, true);
    }

    _updateHeatmapChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("heatmapChart");
        if (!chartDom) {
            return;
        }

        if (!this.heatmapChart) {
            this.heatmapChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.heatmapChart) {
                    this.heatmapChart.resize();
                }
            });
        }

        const heatmapData = this.state.stats.heatmap_data || {
            x_axis: [],
            y_axis: [],
            data: [],
            max_value: 0,
        };

        const option = {
            tooltip: {
                position: "top",
                formatter: (params) => {
                    const xLabel = heatmapData.x_axis[params.data[0]];
                    const yLabel = heatmapData.y_axis[params.data[1]];
                    const value = this.formatCurrency(params.data[2]);
                    return `${yLabel}<br/>${xLabel}<br/>งบประมาณ: ${value} บาท`;
                },
            },
            grid: {
                left: "20%",
                right: "10%",
                top: "10%",
                bottom: "15%",
            },
            xAxis: {
                type: "category",
                data: heatmapData.x_axis,
                splitArea: {show: true},
                axisLabel: {
                    rotate: 30,
                    fontSize: 10,
                },
            },
            yAxis: {
                type: "category",
                data: heatmapData.y_axis,
                splitArea: {show: true},
                axisLabel: {
                    fontSize: 10,
                },
            },
            visualMap: {
                min: 0,
                max: heatmapData.max_value || 1,
                calculable: true,
                orient: "horizontal",
                left: "center",
                bottom: "0%",
                inRange: {
                    color: ["#f0f9e8", "#bae4bc", "#7bccc4", "#43a2ca", "#0868ac"],
                },
                formatter: (value) => this.formatCurrency(value),
            },
            series: [
                {
                    name: "งบประมาณ",
                    type: "heatmap",
                    data: heatmapData.data,
                    label: {
                        show: false,
                    },
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowColor: "rgba(0, 0, 0, 0.5)",
                        },
                    },
                },
            ],
        };

        this.heatmapChart.setOption(option, true);
    }

    _updateFundPieChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("fundPieChart");
        if (!chartDom) {
            return;
        }

        if (!this.fundPieChart) {
            this.fundPieChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.fundPieChart) {
                    this.fundPieChart.resize();
                }
            });
        }

        const data = this.state.stats.fund_pie_data || [];

        const option = {
            tooltip: {
                trigger: "item",
                formatter: (params) => {
                    const value = this.formatCurrency(params.value);
                    return `${params.name}: ${value} บาท (${params.percent.toFixed(1)}%)`;
                },
            },
            title: {
                text: "งบประมาณตามกองทุน",
                left: "center",
                top: 0,
                textStyle: {
                    fontSize: 18,
                    fontWeight: "bold",
                    color: "#3c3c41",
                },
            },
            legend: {
                orient: 'vertical',
                right: 0,
                top: 'center',
            },
            series: [
                {
                    name: "กองทุน",
                    type: "pie",
                    radius: '60%',
                    center: ['30%', '50%'],
                    label: {
                        show: true,
                        formatter: (params) => {
                            if (params.percent < 5) return "";
                            return `${params.percent.toFixed(1)}%`;
                        },
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
                    data: data,
                },
            ],
        };

        this.fundPieChart.setOption(option, true);
    }

    _updateAccountTypePieChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("accountTypePieChart");
        if (!chartDom) {
            return;
        }

        if (!this.accountTypePieChart) {
            this.accountTypePieChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.accountTypePieChart) {
                    this.accountTypePieChart.resize();
                }
            });
        }

        const data = this.state.stats.account_type_pie_data || [];

        const option = {
            tooltip: {
                trigger: "item",
                formatter: (params) => {
                    const value = this.formatCurrency(params.value);
                    return `${params.name}: ${value} บาท (${params.percent.toFixed(1)}%)`;
                },
            },
            title: {
                text: "งบประมาณตามประเภทงบ",
                left: "center",
                top: 0,
                textStyle: {
                    fontSize: 18,
                    fontWeight: "bold",
                    color: "#3c3c41",
                },
            },
            legend: {
                orient: 'vertical',
                right: 0,
                top: 'center',
            },
            series: [
                {
                    name: "ประเภทงบ",
                    type: "pie",
                    radius: '60%',
                    center: ['30%', '50%'],
                    label: {
                        show: true,
                        formatter: (params) => {
                            if (params.percent < 5) return "";
                            return `${params.percent.toFixed(0)}%`;
                        },
                        position: "inside",
                        fontSize: 10,
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
                    data: data,
                },
            ],
        };

        this.accountTypePieChart.setOption(option, true);
    }

    _updateDepartmentPieChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("departmentPieChart");
        if (!chartDom) {
            return;
        }

        if (!this.departmentPieChart) {
            this.departmentPieChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.departmentPieChart) {
                    this.departmentPieChart.resize();
                }
            });
        }

        const data = this.state.stats.department_pie_data || [];

        const option = {
            tooltip: {
                trigger: "item",
                formatter: (params) => {
                    const value = this.formatCurrency(params.value);
                    return `${params.name}: ${value} บาท (${params.percent.toFixed(1)}%)`;
                },
            },
            title: {
                text: "งบประมาณตามหน่วยงาน",
                left: "center",
                top: 0,
                textStyle: {
                    fontSize: 18,
                    fontWeight: "bold",
                    color: "#3c3c41",
                },
            },
            legend: {
                orient: 'vertical',
                type: 'scroll',
                right: 0,
                top: 'center',
            },
            series: [
                {
                    name: "หน่วยงาน",
                    type: "pie",
                    radius: '70%',
                    center: ['40%', '50%'],
                    label: {
                        show: true,
                        formatter: (params) => {
                            if (params.percent < 5) return "";
                            return `${params.percent.toFixed(0)}%`;
                        },
                        position: "inside",
                        fontSize: 10,
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
                    data: data,
                },
            ],
        };

        this.departmentPieChart.setOption(option, true);
    }

    _updateStackedBarChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("stackedBarChart");
        if (!chartDom) {
            return;
        }

        if (!this.stackedBarChart) {
            this.stackedBarChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.stackedBarChart) {
                    this.stackedBarChart.resize();
                }
            });
        }

        const data = this.state.stats.stacked_bar_data || {departments: [], series: []};

        const option = {
            tooltip: {
                trigger: "axis",
                axisPointer: {type: "shadow"},
                formatter: (params) => {
                    let result = `<strong>${params[0].axisValue}</strong><br/>`;
                    params.forEach((p) => {
                        if (p.value > 0) {
                            result += `${p.marker} ${p.seriesName}: ${p.value}%<br/>`;
                        }
                    });
                    return result;
                },
            },
            title: {
                text: "สัดส่วนการจัดสรรงบประมาณรายหน่วยงาน x ประเภทงบ",
                left: "center",
                top: 0,
                textStyle: {
                    fontSize: 18,
                    fontWeight: "bold",
                    color: "#3c3c41",
                },
            },
            legend: {
                orient: 'horizontal',
                top: 40,
                left: 'center',
            },
            grid: {
                left: "20%",
                right: "5%",
                bottom: "5%",
                top: "15%",
            },
            xAxis: {
                type: "value",
                max: 100,
                axisLabel: {
                    formatter: "{value}%",
                },
            },
            yAxis: {
                type: "category",
                data: data.departments,
                axisLabel: {
                    fontSize: 10,
                    width: 120,
                    overflow: "truncate",
                },
            },
            series: data.series.map((s) => ({
                name: s.name,
                type: "bar",
                stack: "total",
                label: {
                    show: true,
                    formatter: (p) => (p.value > 8 ? `${p.value}%` : ""),
                    fontSize: 10,
                },
                emphasis: {
                    focus: "series",
                },
                data: s.data,
            })),
        };

        this.stackedBarChart.setOption(option, true);
    }

    _updateActivitySankeyChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("activitySankeyChart");
        if (!chartDom) {
            return;
        }

        if (!this.activitySankeyChart) {
            this.activitySankeyChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.activitySankeyChart) {
                    this.activitySankeyChart.resize();
                }
            });
        }

        const sankeyData = this.state.stats.activity_sankey_data || {nodes: [], links: []};

        const option = {
            title: {
                text: "การไหลของงบประมาณตามกิจกรรม (ด้าน → แผนงาน → กิจกรรม)",
                left: "center",
                top: 0,
                textStyle: {
                    fontSize: 18,
                    fontWeight: "bold",
                    color: "#3c3c41",
                },
            },
            tooltip: {
                trigger: "item",
                triggerOn: "mousemove",
                formatter: (params) => {
                    if (params.dataType === "edge") {
                        const value = this.formatCurrency(params.value);
                        return `${params.data.source}<br/>→ ${params.data.target}<br/>งบประมาณ: ${value} บาท`;
                    }
                    return params.name;
                },
            },
            series: [
                {
                    type: "sankey",
                    data: sankeyData.nodes,
                    links: sankeyData.links,
                    emphasis: {focus: "adjacency"},
                    lineStyle: {
                        color: "gradient",
                        curveness: 0.5,
                    },
                    label: {
                        fontSize: 10,
                        formatter: (params) => {
                            // Remove prefix for cleaner display
                            return params.name.replace(/^(ด้าน|แผนงาน|กิจกรรม): /, "");
                        },
                    },
                    nodeWidth: 20,
                    nodeGap: 10,
                    layoutIterations: 32,
                    top: 50,
                    bottom: 20,
                },
            ],
        };

        this.activitySankeyChart.setOption(option, true);
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
        if (this.activityTreemapChart) {
            this.activityTreemapChart.dispose();
            this.activityTreemapChart = null;
        }
        if (this.fundTreemapChart) {
            this.fundTreemapChart.dispose();
            this.fundTreemapChart = null;
        }
        if (this.deptAccountChart) {
            this.deptAccountChart.dispose();
            this.deptAccountChart = null;
        }
        if (this.accountOnlyChart) {
            this.accountOnlyChart.dispose();
            this.accountOnlyChart = null;
        }
        if (this.sunburstChart) {
            this.sunburstChart.dispose();
            this.sunburstChart = null;
        }
        if (this.sankeyChart) {
            this.sankeyChart.dispose();
            this.sankeyChart = null;
        }
        if (this.heatmapChart) {
            this.heatmapChart.dispose();
            this.heatmapChart = null;
        }
        if (this.fundPieChart) {
            this.fundPieChart.dispose();
            this.fundPieChart = null;
        }
        if (this.accountTypePieChart) {
            this.accountTypePieChart.dispose();
            this.accountTypePieChart = null;
        }
        if (this.departmentPieChart) {
            this.departmentPieChart.dispose();
            this.departmentPieChart = null;
        }
        if (this.stackedBarChart) {
            this.stackedBarChart.dispose();
            this.stackedBarChart = null;
        }
        if (this.activitySankeyChart) {
            this.activitySankeyChart.dispose();
            this.activitySankeyChart = null;
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
            } else if (tabId === "expense-activity") {
                this._updateActivityTreeMap();
            } else if (tabId === "expense-fund") {
                this._updateFundTreeMap();
            } else if (tabId === "dept-account") {
                this._updateDeptAccountTreeMap();
            } else if (tabId === "account-only") {
                this._updateAccountOnlyTreeMap();
            } else if (tabId === "sunburst") {
                this._updateSunburstChart();
            } else if (tabId === "sankey") {
                this._updateSankeyChart();
            } else if (tabId === "heatmap") {
                this._updateHeatmapChart();
            } else if (tabId === "executive") {
                this._updateFundPieChart();
                this._updateAccountTypePieChart();
                this._updateDepartmentPieChart();
                this._updateStackedBarChart();
                this._updateActivitySankeyChart();
            }
            // "table" tab doesn't need chart initialization
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
