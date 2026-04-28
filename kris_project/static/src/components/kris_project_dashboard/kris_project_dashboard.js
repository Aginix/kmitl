/** @odoo-module **/

import {
    Component,
    onMounted,
    onPatched,
    onWillStart,
    onWillUnmount,
    useState,
} from "@odoo/owl";

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

const THAI_MONTHS = [
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
];

export class KrisProjectDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading: false,
            filters: {
                date_from: "",
                date_to: "",
                category_id: null,
                type_id: null,
                fiscal_year_id: null,
            },
            data: {
                cards: {
                    total_estimated: 0,
                    total_received: 0,
                    kris_actual: 0,
                    kris_estimated: 0,
                    achievement_pct: 0,
                },
                by_type: [],
                combo: {current_year: 0, prev_year: 0, current: [], prev: []},
                top_leaders: [],
                heatmap: [],
                filter_options: {
                    categories: [],
                    types: [],
                    fiscal_years: [],
                },
            },
        });

        this.byTypeChart = null;
        this.comboChart = null;
        this.leadersChart = null;
        this.heatmapChart = null;
        this._shouldInitCharts = false;

        onWillStart(async () => {
            await this._loadECharts();
            await this.loadData();
        });

        onMounted(() => {
            this._initAllCharts();
        });

        onPatched(() => {
            if (this._shouldInitCharts) {
                this._shouldInitCharts = false;
                this._initAllCharts();
            }
        });

        onWillUnmount(() => {
            this._destroyAllCharts();
        });
    }

    async _loadECharts() {
        if (typeof echarts !== "undefined") return;
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
            const filters = {...this.state.filters};
            Object.keys(filters).forEach((k) => {
                if (filters[k] === "") filters[k] = null;
            });
            const data = await this.orm.call(
                "kris.project",
                "get_dashboard_data",
                [filters]
            );
            this.state.data = data;
        } catch (e) {
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล", {type: "danger"});
            console.error("Dashboard load error:", e);
        } finally {
            this.state.loading = false;
        }
        this._shouldInitCharts = true;
    }

    async onApplyFilters() {
        await this.loadData();
    }

    onResetFilters() {
        this.state.filters.date_from = "";
        this.state.filters.date_to = "";
        this.state.filters.category_id = null;
        this.state.filters.type_id = null;
        this.state.filters.fiscal_year_id = null;
        this.loadData();
    }

    onCategoryChange(ev) {
        const val = ev.target.value;
        this.state.filters.category_id = val ? parseInt(val) : null;
        this.state.filters.type_id = null;
    }

    onTypeChange(ev) {
        const val = ev.target.value;
        this.state.filters.type_id = val ? parseInt(val) : null;
    }

    onFiscalYearChange(ev) {
        const val = ev.target.value;
        this.state.filters.fiscal_year_id = val ? parseInt(val) : null;
    }

    get filteredTypes() {
        const catId = this.state.filters.category_id;
        const types = this.state.data.filter_options.types || [];
        if (!catId) return types;
        return types.filter((t) => t.category_id === catId);
    }

    formatCurrency(value) {
        if (!value && value !== 0) return "0.00";
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    }

    formatPct(value) {
        return (value || 0).toFixed(1);
    }

    _initAllCharts() {
        setTimeout(() => {
            this._destroyAllCharts();
            this._initByTypeChart();
            this._initLeadersChart();
            this._initComboChart();
            this._initHeatmapChart();
        }, 100);
    }

    _destroyAllCharts() {
        [
            this.byTypeChart,
            this.comboChart,
            this.leadersChart,
            this.heatmapChart,
        ].forEach((c) => {
            if (c) c.dispose();
        });
        this.byTypeChart = null;
        this.comboChart = null;
        this.leadersChart = null;
        this.heatmapChart = null;
    }

    _initByTypeChart() {
        const el = document.getElementById("kris_by_type_chart");
        if (!el || typeof echarts === "undefined") return;
        const data = this.state.data.by_type || [];
        if (!data.length) {
            el.innerHTML =
                '<div class="text-center text-muted py-5">ไม่มีข้อมูล</div>';
            return;
        }
        this.byTypeChart = echarts.init(el);
        const reversed = [...data].reverse();
        this.byTypeChart.setOption({
            tooltip: {trigger: "axis", axisPointer: {type: "shadow"}},
            legend: {data: ["ประมาณการ KRIS", "รับจริง KRIS"], top: 0},
            grid: {left: 16, right: 20, top: 40, bottom: 8, containLabel: true},
            xAxis: {
                type: "value",
                axisLabel: {formatter: (v) => this.formatCurrency(v)},
            },
            yAxis: {
                type: "category",
                data: reversed.map((d) => d.label),
                axisLabel: {fontSize: 11, overflow: "truncate", width: 120},
            },
            series: [
                {
                    name: "ประมาณการ KRIS",
                    type: "bar",
                    data: reversed.map((d) => d.kris_estimated),
                    itemStyle: {color: "#a8c7fa"},
                },
                {
                    name: "รับจริง KRIS",
                    type: "bar",
                    data: reversed.map((d) => d.kris_actual),
                    itemStyle: {color: "#1a73e8"},
                },
            ],
        });
    }

    _initLeadersChart() {
        const el = document.getElementById("kris_leaders_chart");
        if (!el || typeof echarts === "undefined") return;
        const data = [...(this.state.data.top_leaders || [])].reverse();
        if (!data.length) {
            el.innerHTML =
                '<div class="text-center text-muted py-5">ไม่มีข้อมูล</div>';
            return;
        }
        this.leadersChart = echarts.init(el);
        this.leadersChart.setOption({
            tooltip: {
                trigger: "axis",
                formatter: (params) => {
                    const p = params[0];
                    return `${p.name}<br/>${this.formatCurrency(p.value)} บาท`;
                },
            },
            grid: {left: 16, right: 20, top: 10, bottom: 8, containLabel: true},
            xAxis: {
                type: "value",
                axisLabel: {formatter: (v) => this.formatCurrency(v)},
            },
            yAxis: {
                type: "category",
                data: data.map((d) => d.name),
                axisLabel: {fontSize: 11, overflow: "truncate", width: 100},
            },
            series: [
                {
                    type: "bar",
                    data: data.map((d) => d.amount),
                    itemStyle: {color: "#34a853"},
                    label: {
                        show: true,
                        position: "right",
                        formatter: (p) => this.formatCurrency(p.value),
                        fontSize: 10,
                    },
                },
            ],
        });
    }

    _initComboChart() {
        const el = document.getElementById("kris_combo_chart");
        if (!el || typeof echarts === "undefined") return;
        this.comboChart = echarts.init(el);
        const combo = this.state.data.combo || {
            current_year: 0,
            prev_year: 0,
            current: [],
            prev: [],
        };
        this.comboChart.setOption({
            tooltip: {trigger: "axis"},
            legend: {
                data: [String(combo.current_year), String(combo.prev_year)],
                top: 0,
            },
            grid: {left: 16, right: 20, top: 40, bottom: 8, containLabel: true},
            xAxis: {type: "category", data: THAI_MONTHS},
            yAxis: {
                type: "value",
                axisLabel: {formatter: (v) => this.formatCurrency(v)},
            },
            series: [
                {
                    name: String(combo.current_year),
                    type: "bar",
                    data: combo.current,
                    itemStyle: {color: "#1a73e8"},
                },
                {
                    name: String(combo.prev_year),
                    type: "line",
                    data: combo.prev,
                    smooth: true,
                    lineStyle: {color: "#fbbc04"},
                    itemStyle: {color: "#fbbc04"},
                },
            ],
        });
    }

    _initHeatmapChart() {
        const el = document.getElementById("kris_heatmap_chart");
        if (!el || typeof echarts === "undefined") return;
        const rows = this.state.data.heatmap || [];
        if (!rows.length) {
            el.innerHTML =
                '<div class="text-center text-muted py-5">ไม่มีข้อมูล</div>';
            return;
        }

        const height = Math.max(200, rows.length * 44 + 80);
        el.style.height = `${height}px`;

        this.heatmapChart = echarts.init(el);
        const xCategories = ["ส่วนกลาง", "คณะ/หน่วยงาน", "KRIS"];
        const yCategories = rows.map((r) => r.name);
        const heatData = [];
        rows.forEach((row, yi) => {
            heatData.push([0, yi, row.central || 0]);
            heatData.push([1, yi, row.faculty_dept || 0]);
            heatData.push([2, yi, row.kris || 0]);
        });
        const maxVal = Math.max(1, ...heatData.map((d) => d[2]));

        this.heatmapChart.setOption({
            tooltip: {
                formatter: (p) => {
                    const xName = xCategories[p.value[0]];
                    const yName = yCategories[p.value[1]];
                    return `${yName} — ${xName}<br/>${this.formatCurrency(p.value[2])} บาท`;
                },
            },
            grid: {left: 16, right: 90, top: 10, bottom: 10, containLabel: true},
            xAxis: {
                type: "category",
                data: xCategories,
                splitArea: {show: true},
            },
            yAxis: {
                type: "category",
                data: yCategories,
                axisLabel: {fontSize: 11},
                splitArea: {show: true},
            },
            visualMap: {
                min: 0,
                max: maxVal,
                calculable: true,
                orient: "vertical",
                right: 0,
                top: "center",
                inRange: {color: ["#f5f5f5", "#1a73e8"]},
            },
            series: [
                {
                    type: "heatmap",
                    data: heatData,
                    label: {
                        show: true,
                        formatter: (p) => {
                            const v = p.value[2];
                            if (!v) return "";
                            return this.formatCurrency(v);
                        },
                        fontSize: 10,
                    },
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowColor: "rgba(0,0,0,0.5)",
                        },
                    },
                },
            ],
        });
    }
}

KrisProjectDashboard.template = "kris_project.KrisProjectDashboard";
KrisProjectDashboard.components = {};
registry.category("actions").add("kris_project_dashboard", KrisProjectDashboard);
