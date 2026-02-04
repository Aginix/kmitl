/** @odoo-module **/

import {Component, onMounted, onWillStart, onWillUnmount, useState} from "@odoo/owl";

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class BudgetAppropriationDashboard extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false
        };

        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.state = useState({
            filters: {
                fiscal_year_id: null,
                source_id: null,
            },
            loading: false,
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

        onWillStart(async () => {
            await this._loadECharts();
            await this.loadData();
        });

        onMounted(() => {
            this._initChart();
        });

        onWillUnmount(() => {
            if (this.chart) {
                this.chart.dispose();
                this.chart = null;
            }
        });
    }

    async _loadECharts() {
        if (typeof echarts !== "undefined") {
            return;
        }
        return new Promise((resolve) => {
            const script = document.createElement("script");
            script.src = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js";
            script.onload = resolve;
            script.onerror = () => {
                console.error("Failed to load ECharts");
                resolve();
            };
            document.head.appendChild(script);
        });
    }

    _initChart() {
        setTimeout(() => this._updateChart(), 100);
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

    async loadData() {
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

            this._updateChart();
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล: " + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
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

BudgetAppropriationDashboard.template = "budget_appropriation_report.BudgetAppropriationDashboard";
BudgetAppropriationDashboard.components = {
    ControlPanel,
};

registry
    .category("actions")
    .add("budget_appropriation_dashboard", BudgetAppropriationDashboard);
