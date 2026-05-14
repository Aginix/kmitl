/** @odoo-module **/
/*
 * Portal-only summary dashboard for budget appropriation.
 * 3 tabs: Overview / Revenue / Expense — shared filter bar.
 * Plain DOM + fetch, ECharts loaded from CDN.
 * Intentionally independent from the backend dashboard component.
 */

(function () {
    "use strict";

    const ECHARTS_URL = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js";
    const REVENUE_COLORS = ["#28a745", "#20c997", "#17a2b8", "#0dcaf0", "#6610f2", "#ffc107", "#fd7e14"];
    const CATEGORY_COLORS = ["#0d6efd", "#20c997", "#fd7e14", "#6f42c1", "#dc3545", "#198754"];
    const FUND_COLORS = ["#198754", "#20c997", "#0dcaf0", "#6f42c1", "#fd7e14", "#dc3545", "#0d6efd", "#ffc107"];
    const ACTIVITY_COLORS = ["#0d6efd", "#6610f2", "#6f42c1", "#d63384", "#dc3545", "#198754"];

    function loadECharts() {
        if (typeof window.echarts !== "undefined") return Promise.resolve();
        return new Promise((resolve) => {
            const script = document.createElement("script");
            script.src = ECHARTS_URL;
            script.onload = resolve;
            script.onerror = () => {
                console.error("Failed to load ECharts");
                resolve();
            };
            document.head.appendChild(script);
        });
    }

    function formatNumber(n) {
        if (!isFinite(n)) return "0";
        return new Intl.NumberFormat("th-TH", {maximumFractionDigits: 0}).format(Math.round(n));
    }

    function formatCompact(n) {
        const abs = Math.abs(n);
        if (abs >= 1e9) return (n / 1e9).toFixed(2) + " พันล้าน";
        if (abs >= 1e6) return (n / 1e6).toFixed(2) + " ล้าน";
        if (abs >= 1e3) return (n / 1e3).toFixed(1) + "K";
        return formatNumber(n);
    }

    function emptyOption(text) {
        return {
            title: {text: text || "ไม่มีข้อมูล", left: "center", top: "center", textStyle: {color: "#adb5bd", fontSize: 14}},
            series: [],
        };
    }

    class PortalSummary {
        constructor(root) {
            this.root = root;
            this.payload = this._readPayload();
            this.charts = {};
            this.activeTab = this._readTabFromUrl() || "overview";
            // Switch the portal layout's .container into full-width mode.
            // Scoped by the body class so it doesn't leak to other pages.
            document.body.classList.add("bap-fullwidth");
            this._setUpdated();
            this._bindFilters();
            this._bindTabs();
            this._activateTab(this.activeTab, false);
            this._render();
            window.addEventListener("resize", () => this._resizeAll());
        }

        _readPayload() {
            try {
                return JSON.parse(this.root.dataset.payload || "{}");
            } catch (e) {
                console.error("Invalid portal payload", e);
                return {};
            }
        }

        _readTabFromUrl() {
            const m = window.location.hash.match(/tab=(overview|revenue|expense)/);
            return m ? m[1] : null;
        }

        _setUpdated() {
            const el = this.root.querySelector("#bapSummaryUpdated");
            if (el) el.textContent = "อัปเดต: " + new Date().toLocaleString("th-TH");
        }

        _bindFilters() {
            const filterEl = this.root.querySelector("#bapSummaryFilters");
            if (!filterEl) return;
            filterEl.querySelectorAll("select[data-filter]").forEach((sel) => {
                sel.addEventListener("change", () => this._fetch());
            });
            const resetBtn = this.root.querySelector("#bapSummaryReset");
            if (resetBtn) {
                resetBtn.addEventListener("click", () => {
                    filterEl.querySelectorAll("select[data-filter]").forEach((sel) => {
                        if (sel.dataset.required) return; // keep required selections
                        if (sel.dataset.filter === "fiscal_year_id") return;
                        sel.value = "";
                    });
                    this._fetch();
                });
            }
        }

        _bindTabs() {
            const nav = this.root.querySelector("#bapTabs");
            if (!nav) return;
            nav.querySelectorAll("a[data-tab]").forEach((a) => {
                a.addEventListener("click", (ev) => {
                    ev.preventDefault();
                    this._activateTab(a.dataset.tab, true);
                });
            });
        }

        _activateTab(tab, pushHash) {
            this.activeTab = tab;
            this.root.querySelectorAll("#bapTabs a[data-tab]").forEach((a) => {
                a.classList.toggle("active", a.dataset.tab === tab);
            });
            this.root.querySelectorAll(".bap-tab-pane").forEach((pane) => {
                pane.classList.toggle("d-none", pane.dataset.pane !== tab);
            });
            if (pushHash) {
                window.location.hash = "tab=" + tab;
            }
            // Re-render the visible tab's charts (lazy resize/init).
            this._renderTab(tab);
        }

        _readFilters() {
            const out = {};
            this.root.querySelectorAll("#bapSummaryFilters select[data-filter]").forEach((sel) => {
                if (sel.value) out[sel.dataset.filter] = sel.value;
            });
            return out;
        }

        async _fetch() {
            const params = this._readFilters();
            this.root.classList.add("opacity-50");
            try {
                const resp = await fetch("/budget/appropriation/portal_summary/data", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({jsonrpc: "2.0", method: "call", params: params}),
                });
                const json = await resp.json();
                if (json && json.result) {
                    this.payload = json.result;
                    this._setUpdated();
                    this._render();
                }
            } catch (err) {
                console.error("Failed to load summary data", err);
            } finally {
                this.root.classList.remove("opacity-50");
            }
        }

        _render() {
            const stats = (this.payload && this.payload.stats) || {};
            this._renderKpi(stats.kpi || {});
            this._renderConcentration(stats.expense || {});
            this._renderExpenseDetailTable(stats.expense || {});
            this._renderRevenueItemsTable(stats.revenue || {});
            this._renderExpenseItemsTable(stats.expense || {});
            if (typeof window.echarts !== "undefined") {
                this._renderTab(this.activeTab);
            }
        }

        _renderTab(tab) {
            if (typeof window.echarts === "undefined") return;
            const stats = (this.payload && this.payload.stats) || {};
            const revenue = stats.revenue || {};
            const expense = stats.expense || {};
            // Small delay so the pane is visible before sizing charts.
            setTimeout(() => {
                if (tab === "overview") {
                    this._renderRevExp(stats.kpi || {});
                    this._renderDonut("#bapChartOverviewRevenue", revenue.by_category || [], REVENUE_COLORS);
                    this._renderDonut("#bapChartOverviewExpense", expense.by_category || [], CATEGORY_COLORS);
                } else if (tab === "revenue") {
                    this._renderDonut("#bapChartRevCategory", revenue.by_category || [], REVENUE_COLORS, true);
                    this._renderRevByDept(revenue.per_department || []);
                    this._renderDeductFlow(revenue.deduct_flow || {});
                    this._renderGenericHeatmap(
                        "#bapChartRevDeptCatHeatmap",
                        revenue.dept_category_heatmap || {},
                        ["#f2fbf3", "#28a745", "#0f3d1d"]
                    );
                } else if (tab === "expense") {
                    this._renderDonut("#bapChartExpCategory", expense.by_category || [], CATEGORY_COLORS);
                    this._renderDonut("#bapChartExpFund", expense.fund_pie || [], FUND_COLORS);
                    this._renderActivity("#bapChartExpActivity", expense.activity_bar || []);
                    this._renderTopDept(expense.department_bar || []);
                    this._renderPersonnel(expense.personnel_ratio || []);
                    this._renderHeatmap(expense.heatmap || {});
                    this._renderFundDeptCatSankey(expense.fund_dept_cat_sankey || {});
                    this._renderGenericHeatmap(
                        "#bapChartExpDeptActivity",
                        expense.dept_activity_heatmap || {},
                        ["#fff4e6", "#fd7e14", "#5a2700"]
                    );
                    this._renderSunburst(expense.activity_sunburst || []);
                }
                this._resizeAll();
            }, 50);
        }

        _setKpi(name, text) {
            this.root.querySelectorAll(`[data-kpi="${name}"]`).forEach((el) => {
                el.textContent = text;
            });
        }

        _renderKpi(kpi) {
            this._setKpi("total_revenue", formatNumber(kpi.total_revenue || 0));
            this._setKpi("total_revenue_gross", formatNumber(kpi.total_revenue_gross || 0));
            this._setKpi("total_revenue_deduct", formatNumber(kpi.total_revenue_deduct || 0));
            this._setKpi("total_expense", formatNumber(kpi.total_expense || 0));
        }

        _renderConcentration(expense) {
            const concentration = expense.concentration || {};
            this._setKpi("exp_top5_pct", (concentration.top5_pct || 0).toFixed(1) + "%");
            this._setKpi("exp_dept_count", concentration.total_dept_count || 0);
            // Personnel / Other percentage over all expense
            const total = (expense.totals && expense.totals.total) || 0;
            let personnel = 0;
            (expense.by_category || []).forEach((c) => {
                if (c.code === "51000") personnel = c.value;
            });
            const personnelPct = total ? (personnel / total) * 100 : 0;
            const otherPct = total ? 100 - personnelPct : 0;
            this._setKpi("exp_personnel_pct", personnelPct.toFixed(1) + "%");
            this._setKpi("exp_other_pct", otherPct.toFixed(1) + "%");
            const pBar = this.root.querySelector('[data-progress="personnel"]');
            const oBar = this.root.querySelector('[data-progress="other"]');
            if (pBar) pBar.style.width = personnelPct.toFixed(2) + "%";
            if (oBar) oBar.style.width = otherPct.toFixed(2) + "%";
        }

        _getChart(selector) {
            const dom = this.root.querySelector(selector);
            if (!dom) return null;
            if (this.charts[selector]) return this.charts[selector];
            const inst = window.echarts.init(dom);
            this.charts[selector] = inst;
            return inst;
        }

        _resizeAll() {
            Object.values(this.charts).forEach((c) => c && c.resize());
        }

        _renderRevExp(kpi) {
            const chart = this._getChart("#bapChartRevExp");
            if (!chart) return;
            const data = [
                {name: "รายรับสุทธิ", value: kpi.total_revenue || 0},
                {name: "รายจ่ายรวม", value: kpi.total_expense || 0},
            ];
            chart.setOption({
                tooltip: {trigger: "item", formatter: (p) => `${p.name}: ${formatNumber(p.value)} (${p.percent}%)`},
                legend: {bottom: 0},
                color: ["#28a745", "#dc3545"],
                series: [{
                    type: "pie",
                    radius: ["45%", "75%"],
                    center: ["50%", "45%"],
                    itemStyle: {borderRadius: 6, borderColor: "#fff", borderWidth: 2},
                    label: {formatter: "{d}%", position: "inside", color: "#fff", fontWeight: "bold"},
                    data: data,
                }],
            }, true);
        }

        _renderDonut(selector, data, colors, withLegend) {
            const chart = this._getChart(selector);
            if (!chart) return;
            if (!data.length) {
                chart.setOption(emptyOption(), true);
                return;
            }
            chart.setOption({
                tooltip: {
                    trigger: "item",
                    formatter: (p) => {
                        const code = p.data && p.data.code ? `[${p.data.code}] ` : "";
                        return `${code}${p.name}<br/>${formatNumber(p.value)} (${p.percent}%)`;
                    },
                },
                legend: withLegend
                    ? {orient: "vertical", left: 0, top: "middle", textStyle: {fontSize: 11}}
                    : {bottom: 0, textStyle: {fontSize: 11}, type: "scroll"},
                color: colors,
                series: [{
                    type: "pie",
                    radius: ["40%", "70%"],
                    center: withLegend ? ["65%", "50%"] : ["50%", "45%"],
                    itemStyle: {borderRadius: 4, borderColor: "#fff", borderWidth: 2},
                    label: {formatter: "{d}%"},
                    data: data,
                }],
            }, true);
        }

        _renderActivity(selector, data) {
            const chart = this._getChart(selector);
            if (!chart) return;
            if (!data.length) {
                chart.setOption(emptyOption(), true);
                return;
            }
            const sorted = data.slice().sort((a, b) => a.value - b.value);
            chart.setOption({
                grid: {left: 140, right: 60, top: 10, bottom: 30},
                xAxis: {type: "value", axisLabel: {formatter: (v) => formatCompact(v)}},
                yAxis: {type: "category", data: sorted.map((d) => d.name), axisLabel: {fontSize: 10, width: 130, overflow: "truncate"}},
                tooltip: {trigger: "item", formatter: (p) => `${p.name}<br/>${formatNumber(p.value)} บาท`},
                series: [{
                    type: "bar",
                    data: sorted.map((d, i) => ({value: d.value, itemStyle: {color: ACTIVITY_COLORS[i % ACTIVITY_COLORS.length]}})),
                    itemStyle: {borderRadius: [0, 4, 4, 0]},
                    label: {show: true, position: "right", formatter: (p) => formatCompact(p.value), fontSize: 10},
                }],
            }, true);
        }

        _renderTopDept(data) {
            const chart = this._getChart("#bapChartExpTopDept");
            if (!chart) return;
            if (!data.length) {
                chart.setOption(emptyOption(), true);
                return;
            }
            const sorted = data.slice().sort((a, b) => a.value - b.value);
            chart.setOption({
                grid: {left: 200, right: 80, top: 10, bottom: 30},
                xAxis: {type: "value", axisLabel: {formatter: (v) => formatCompact(v)}},
                yAxis: {
                    type: "category",
                    data: sorted.map((d) => `[${d.code}] ${d.name}`),
                    axisLabel: {fontSize: 11, width: 190, overflow: "truncate"},
                },
                tooltip: {trigger: "item", formatter: (p) => `${p.name}<br/>รายจ่าย: ${formatNumber(p.value)} บาท`},
                series: [{
                    type: "bar",
                    data: sorted.map((d) => d.value),
                    itemStyle: {color: "#dc3545", borderRadius: [0, 4, 4, 0]},
                    label: {show: true, position: "right", formatter: (p) => formatCompact(p.value), fontSize: 10},
                }],
            }, true);
        }

        _renderPersonnel(data) {
            const chart = this._getChart("#bapChartExpPersonnel");
            if (!chart) return;
            if (!data.length) {
                chart.setOption(emptyOption(), true);
                return;
            }
            const limited = data.slice(0, 15).reverse();
            const labels = limited.map((d) => `[${d.code}] ${d.name}`);
            chart.setOption({
                grid: {left: 180, right: 50, top: 30, bottom: 30},
                tooltip: {
                    trigger: "axis", axisPointer: {type: "shadow"},
                    formatter: (params) => {
                        const lines = [params[0].axisValue];
                        params.forEach((p) => {
                            lines.push(`${p.marker} ${p.seriesName}: ${formatNumber(p.value)}`);
                        });
                        return lines.join("<br/>");
                    },
                },
                legend: {data: ["บุคลากร", "อื่น ๆ"], top: 0},
                xAxis: {type: "value", axisLabel: {formatter: (v) => formatCompact(v)}},
                yAxis: {type: "category", data: labels, axisLabel: {fontSize: 11, width: 170, overflow: "truncate"}},
                series: [
                    {
                        name: "บุคลากร", type: "bar", stack: "x",
                        data: limited.map((d) => d.personnel),
                        itemStyle: {color: "#0d6efd"},
                        label: {
                            show: true, position: "insideLeft", color: "#fff", fontSize: 10,
                            formatter: (p) => p.value > 0 ? `${limited[p.dataIndex].pct_personnel.toFixed(0)}%` : "",
                        },
                    },
                    {
                        name: "อื่น ๆ", type: "bar", stack: "x",
                        data: limited.map((d) => d.other),
                        itemStyle: {color: "#adb5bd"},
                    },
                ],
            }, true);
        }

        _renderHeatmap(data) {
            this._renderGenericHeatmap(
                "#bapChartExpHeatmap",
                data,
                ["#f0f4ff", "#0d6efd", "#0a2972"]
            );
        }

        _renderGenericHeatmap(selector, data, colors) {
            const chart = this._getChart(selector);
            if (!chart) return;
            if (!data || !data.x || !data.y || !data.x.length || !data.y.length) {
                chart.setOption(emptyOption(), true);
                return;
            }
            chart.setOption({
                tooltip: {
                    position: "top",
                    formatter: (p) => `${data.y[p.value[1]]}<br/>${data.x[p.value[0]]}<br/>${formatNumber(p.value[2])} บาท`,
                },
                grid: {left: 220, right: 40, top: 60, bottom: 30},
                xAxis: {
                    type: "category", data: data.x, splitArea: {show: true},
                    axisLabel: {fontSize: 11, interval: 0, rotate: data.x.length > 6 ? 20 : 0},
                    position: "top",
                },
                yAxis: {type: "category", data: data.y, splitArea: {show: true}, axisLabel: {fontSize: 10, width: 210, overflow: "truncate"}},
                visualMap: {
                    min: 0, max: data.max || 1, calculable: true, orient: "horizontal",
                    left: "center", bottom: 0,
                    inRange: {color: colors},
                    formatter: (v) => formatCompact(v),
                },
                series: [{
                    type: "heatmap",
                    data: data.data,
                    label: {show: true, formatter: (p) => p.value[2] > 0 ? formatCompact(p.value[2]) : "", fontSize: 9},
                    emphasis: {itemStyle: {shadowBlur: 10, shadowColor: "rgba(0,0,0,0.3)"}},
                }],
            }, true);
        }

        _renderFundDeptCatSankey(data) {
            const chart = this._getChart("#bapChartExpFundDeptCat");
            if (!chart) return;
            if (!data || !data.nodes || !data.nodes.length || !data.links || !data.links.length) {
                chart.setOption(emptyOption("ไม่มีข้อมูลในตัวกรองนี้"), true);
                return;
            }
            chart.setOption({
                tooltip: {
                    trigger: "item",
                    formatter: (p) => {
                        if (p.dataType === "edge") {
                            return `${p.data.source}<br/>→ ${p.data.target}<br/>${formatNumber(p.data.value)} บาท`;
                        }
                        return p.data.name;
                    },
                },
                series: [{
                    type: "sankey",
                    left: 10, right: 220, top: 10, bottom: 10,
                    nodeAlign: "justify",
                    nodeGap: 8,
                    data: data.nodes,
                    links: data.links,
                    label: {fontSize: 10},
                    lineStyle: {color: "gradient", curveness: 0.5, opacity: 0.55},
                    emphasis: {focus: "adjacency"},
                }],
            }, true);
        }

        _renderSunburst(data) {
            const chart = this._getChart("#bapChartExpActivitySunburst");
            if (!chart) return;
            if (!data || !data.length) {
                chart.setOption(emptyOption(), true);
                return;
            }
            chart.setOption({
                tooltip: {
                    formatter: (p) => `${p.treePathInfo.map((n) => n.name).filter(Boolean).join(" / ")}<br/>${formatNumber(p.value)} บาท`,
                },
                series: [{
                    type: "sunburst",
                    radius: ["10%", "92%"],
                    sort: (a, b) => b.value - a.value,
                    data: data,
                    emphasis: {focus: "ancestor"},
                    levels: [
                        {},
                        {r0: "10%", r: "40%", itemStyle: {borderWidth: 2}, label: {rotate: "tangential", fontSize: 12}},
                        {r0: "40%", r: "70%", itemStyle: {borderWidth: 1}, label: {fontSize: 10}},
                        {r0: "70%", r: "92%", label: {position: "outside", padding: 3, silent: false, fontSize: 9}, itemStyle: {borderWidth: 1}},
                    ],
                    label: {minAngle: 12},
                }],
            }, true);
        }

        // ------------- Revenue charts -------------
        _renderRevByDept(data) {
            const chart = this._getChart("#bapChartRevByDept");
            if (!chart) return;
            if (!data.length) {
                chart.setOption(emptyOption(), true);
                return;
            }
            const limited = data.slice(0, 15).reverse();
            const labels = limited.map((d) => `[${d.code}] ${d.name}`);
            chart.setOption({
                grid: {left: 180, right: 60, top: 30, bottom: 30},
                tooltip: {
                    trigger: "axis", axisPointer: {type: "shadow"},
                    formatter: (params) => {
                        const lines = [params[0].axisValue];
                        params.forEach((p) => {
                            lines.push(`${p.marker} ${p.seriesName}: ${formatNumber(p.value)}`);
                        });
                        return lines.join("<br/>");
                    },
                },
                legend: {data: ["รายรับสุทธิ", "หักโอน"], top: 0},
                xAxis: {type: "value", axisLabel: {formatter: (v) => formatCompact(v)}},
                yAxis: {type: "category", data: labels, axisLabel: {fontSize: 11, width: 170, overflow: "truncate"}},
                series: [
                    {
                        name: "รายรับสุทธิ", type: "bar", stack: "x",
                        data: limited.map((d) => d.net),
                        itemStyle: {color: "#28a745"},
                        label: {show: true, position: "insideLeft", color: "#fff", fontSize: 10, formatter: (p) => p.value > 0 ? formatCompact(p.value) : ""},
                    },
                    {
                        name: "หักโอน", type: "bar", stack: "x",
                        data: limited.map((d) => d.deduct),
                        itemStyle: {color: "#fd7e14"},
                        label: {show: true, position: "insideRight", color: "#fff", fontSize: 10, formatter: (p) => p.value > 0 ? formatCompact(p.value) : ""},
                    },
                ],
            }, true);
        }

        _renderDeductFlow(data) {
            const chart = this._getChart("#bapChartRevDeductFlow");
            if (!chart) return;
            if (!data || !data.nodes || !data.nodes.length || !data.links || !data.links.length) {
                chart.setOption(emptyOption("ไม่มีรายการหักโอนในตัวกรองนี้"), true);
                return;
            }
            // Cap to top 50 links by value to keep chart readable
            const links = data.links.slice().sort((a, b) => b.value - a.value).slice(0, 50);
            const usedNames = new Set();
            links.forEach((l) => {
                usedNames.add(l.source);
                usedNames.add(l.target);
            });
            const nodes = data.nodes.filter((n) => usedNames.has(n.name));
            chart.setOption({
                tooltip: {
                    trigger: "item",
                    formatter: (p) => {
                        if (p.dataType === "edge") {
                            return `${p.data.source}<br/>→ ${p.data.target}<br/>${formatNumber(p.data.value)} บาท`;
                        }
                        return p.data.name;
                    },
                },
                series: [{
                    type: "sankey",
                    left: 20, right: 200, top: 20, bottom: 20,
                    nodeAlign: "justify",
                    data: nodes,
                    links: links,
                    label: {fontSize: 11},
                    lineStyle: {color: "gradient", curveness: 0.5},
                    emphasis: {focus: "adjacency"},
                }],
            }, true);
        }

        // ------------- Tables -------------
        _renderRevenueItemsTable(revenue) {
            const tbody = this.root.querySelector("#bapTableRevenueItems tbody");
            if (!tbody) return;
            const items = revenue.top_items || [];
            tbody.innerHTML = "";
            if (!items.length) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3">ไม่มีข้อมูล</td></tr>`;
                return;
            }
            items.forEach((row, idx) => {
                const tr = document.createElement("tr");
                if (row.is_deduct) tr.classList.add("table-warning");
                tr.innerHTML = `
                    <td>${idx + 1}</td>
                    <td><code>${row.code || "-"}</code> ${row.is_deduct ? '<span class="badge text-bg-warning">หักโอน</span>' : ''}</td>
                    <td>${row.name || ""}</td>
                    <td><span class="text-muted small">[${row.department_code || "-"}]</span> ${row.department || ""}</td>
                    <td class="text-end fw-semibold">${formatNumber(row.value || 0)}</td>`;
                tbody.appendChild(tr);
            });
        }

        _renderExpenseItemsTable(expense) {
            const tbody = this.root.querySelector("#bapTableExpenseItems tbody");
            if (!tbody) return;
            const items = expense.top_items || [];
            tbody.innerHTML = "";
            if (!items.length) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-3">ไม่มีข้อมูล</td></tr>`;
                return;
            }
            items.forEach((row, idx) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${idx + 1}</td>
                    <td><code>${row.code || "-"}</code></td>
                    <td>${row.name || ""}</td>
                    <td><span class="text-muted small">[${row.department_code || "-"}]</span> ${row.department || ""}</td>
                    <td class="small text-muted">${row.fund || ""}</td>
                    <td class="text-end fw-semibold">${formatNumber(row.value || 0)}</td>`;
                tbody.appendChild(tr);
            });
        }

        _renderExpenseDetailTable(expense) {
            const table = this.root.querySelector("#bapSummaryTable");
            if (!table) return;
            const categories = expense.categories || [];
            const rows = expense.department_table || [];
            const tbody = table.querySelector("tbody");
            const totals = {};
            let grand = 0;
            categories.forEach((c) => (totals[c.code] = 0));

            tbody.innerHTML = "";
            rows.forEach((row) => {
                const tr = document.createElement("tr");
                const tdName = document.createElement("td");
                tdName.innerHTML = `<span class="dept-code">[${row.code || "-"}]</span> ${row.name || ""}`;
                tr.appendChild(tdName);
                categories.forEach((c) => {
                    const v = (row.breakdown || {})[c.code] || 0;
                    totals[c.code] += v;
                    const td = document.createElement("td");
                    td.className = "amount-cell text-end" + (v ? "" : " zero");
                    td.textContent = v ? formatNumber(v) : "-";
                    tr.appendChild(td);
                });
                const tdTotal = document.createElement("td");
                tdTotal.className = "amount-cell text-end fw-semibold";
                tdTotal.textContent = formatNumber(row.value || 0);
                tr.appendChild(tdTotal);
                grand += row.value || 0;
                tbody.appendChild(tr);
            });

            categories.forEach((c) => {
                const footCell = table.querySelector(`[data-foot="${c.code}"]`);
                if (footCell) footCell.textContent = formatNumber(totals[c.code] || 0);
            });
            const grandCell = table.querySelector('[data-foot="total"]');
            if (grandCell) grandCell.textContent = formatNumber(grand);

            if (!rows.length) {
                tbody.innerHTML = `<tr><td colspan="${categories.length + 2}" class="text-center text-muted py-3">ไม่มีข้อมูล</td></tr>`;
            }
        }
    }

    function boot() {
        const root = document.getElementById("bapSummaryRoot");
        if (!root) return;
        loadECharts().then(() => new PortalSummary(root));
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
