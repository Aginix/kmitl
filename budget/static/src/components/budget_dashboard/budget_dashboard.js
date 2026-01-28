/** @odoo-module */

import {Component, onWillStart, onMounted, onPatched, useState, useRef} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {loadJS} from "@web/core/assets";

export class BudgetDashboard extends Component {
    static template = "budget.BudgetDashboard";

    setup() {
        this.orm = useService("orm");
        this.chartRefs = {};
        this.charts = {};

        this.state = useState({
            loading: false,
            filters: {
                fiscal_year_id: null,
                source_id: null,
            },
            filterOptions: {
                fiscal_years: [],
                sources: [],
            },
            stats: {
                total_appropriation: 0,
                total_balance: 0,
                disbursement: 0,
                disbursement_percent: 0,
                budget_breakdown: [],
            },
        });

        onWillStart(async () => {
            await loadJS("https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js");
            await this.loadFilterOptions();
            await this.loadData();
        });

        onMounted(() => {
            this.renderCharts();
        });

        onPatched(() => {
            this.renderCharts();
        });
    }

    async loadFilterOptions() {
        try {
            const options = await this.orm.call(
                "budget.dashboard",
                "get_filter_options",
                []
            );
            this.state.filterOptions = options;

            // Set default fiscal year to first one (required)
            if (options.fiscal_years.length > 0) {
                this.state.filters.fiscal_year_id = options.fiscal_years[0].id;
            }
        } catch (error) {
            console.error("Error loading filter options:", error);
        }
    }

    async loadData() {
        if (!this.state.filters.fiscal_year_id) {
            return;
        }
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "budget.dashboard",
                "get_dashboard_data",
                [this.state.filters]
            );
            this.state.stats = data;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    renderCharts() {
        if (this.state.loading || !this.state.stats.budget_breakdown) {
            return;
        }

        // Dispose existing charts
        Object.values(this.charts).forEach((chart) => {
            if (chart) {
                chart.dispose();
            }
        });
        this.charts = {};

        // Render pie chart for each budget category
        this.state.stats.budget_breakdown.forEach((category, index) => {
            const chartEl = document.getElementById(`budget-chart-${index}`);
            if (!chartEl || !window.echarts) {
                return;
            }

            const chart = window.echarts.init(chartEl);
            this.charts[index] = chart;

            const disbursement = Math.max(0, category.disbursement);
            const balance = Math.max(0, category.balance);

            const option = {
                tooltip: {
                    trigger: "item",
                    formatter: (params) => {
                        return `${params.name}: ${this.formatCurrency(params.value)} บาท (${params.percent}%)`;
                    },
                },
                legend: {
                    orient: "horizontal",
                    bottom: 0,
                    data: ["เบิกจ่าย", "คงเหลือ"],
                },
                series: [
                    {
                        type: "pie",
                        radius: ["40%", "70%"],
                        center: ["50%", "45%"],
                        avoidLabelOverlap: false,
                        itemStyle: {
                            borderRadius: 4,
                            borderColor: "#fff",
                            borderWidth: 2,
                        },
                        label: {
                            show: false,
                        },
                        emphasis: {
                            label: {
                                show: true,
                                fontSize: 14,
                                fontWeight: "bold",
                            },
                        },
                        data: [
                            {
                                value: disbursement,
                                name: "เบิกจ่าย",
                                itemStyle: {color: "#dc3545"},
                            },
                            {
                                value: balance,
                                name: "คงเหลือ",
                                itemStyle: {color: "#28a745"},
                            },
                        ],
                    },
                ],
            };

            chart.setOption(option);
        });

        // Handle window resize
        window.addEventListener("resize", () => {
            Object.values(this.charts).forEach((chart) => {
                if (chart) {
                    chart.resize();
                }
            });
        });
    }

    async onFiscalYearChange(ev) {
        const value = ev.target.value;
        this.state.filters.fiscal_year_id = value ? parseInt(value) : null;
        await this.loadData();
    }

    async onSourceChange(ev) {
        const value = ev.target.value;
        this.state.filters.source_id = value ? parseInt(value) : null;
        await this.loadData();
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(amount);
    }

    formatPercent(value) {
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    }

    get selectedFiscalYearName() {
        const fy = this.state.filterOptions.fiscal_years.find(
            (f) => f.id === this.state.filters.fiscal_year_id
        );
        return fy ? fy.name : "";
    }
}

registry.category("actions").add("budget_dashboard", BudgetDashboard);
