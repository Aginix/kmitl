/** @odoo-module **/

import {Component, onMounted, onWillStart, onWillUnmount, useState} from "@odoo/owl";

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class ProcurementPlanDashboard extends Component {
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
                in_progress_count: 0,
                done_count: 0,
                state_pie_data: [],
                table_data: [],
            },
            filterOptions: {
                fiscal_years: [],
                departments: [],
                sources: [],
            },
        });

        this.statePieChart = null;

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

    async loadData() {
        this.state.loading = true;
        try {
            const response = await this.rpc("/procurement_plan/dashboard/data", {
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
        }, 100);
    }

    _disposeCharts() {
        if (this.statePieChart) {
            this.statePieChart.dispose();
            this.statePieChart = null;
        }
    }

    _updateStatePieChart() {
        if (typeof echarts === "undefined") {
            return;
        }

        const chartDom = document.getElementById("statePieChart");
        if (!chartDom) {
            return;
        }

        // Check if existing chart instance is attached to a different/stale DOM element
        if (this.statePieChart) {
            const existingDom = this.statePieChart.getDom();
            if (!existingDom || !document.body.contains(existingDom) || existingDom !== chartDom) {
                this.statePieChart.dispose();
                this.statePieChart = null;
            }
        }

        if (!this.statePieChart) {
            this.statePieChart = echarts.init(chartDom);
            window.addEventListener("resize", () => {
                if (this.statePieChart) {
                    this.statePieChart.resize();
                }
            });
        }

        const pieData = this.state.stats.state_pie_data || [];

        const option = {
            tooltip: {
                trigger: "item",
                formatter: (params) => {
                    return `${params.name}: ${params.value} รายการ (${params.percent.toFixed(1)}%)`;
                },
            },
            legend: {
                orient: "vertical",
                right: "5%",
                top: "center",
            },
            color: ["#6c757d", "#17a2b8", "#ffc107", "#007bff", "#28a745", "#dc3545"],
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
                        formatter: (params) => {
                            if (params.value === 0) return "";
                            return `${params.percent.toFixed(0)}%`;
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
                    data: pieData,
                },
            ],
        };

        this.statePieChart.setOption(option, true);
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

    onRowClick(planId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "procurement.plan",
            res_id: planId,
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
            to_verify: "badge bg-info",
            verified: "badge bg-warning",
            in_progress: "badge bg-primary",
            done: "badge bg-success",
            cancel: "badge bg-danger",
        };
        return classes[state] || "badge bg-secondary";
    }
}

ProcurementPlanDashboard.template = "procurement_plan.ProcurementPlanDashboard";
ProcurementPlanDashboard.components = {
    ControlPanel,
};

registry
    .category("actions")
    .add("procurement_plan_dashboard", ProcurementPlanDashboard);
