/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { EChart } from "./echart";

// แหล่งเงิน is a single, mandatory scope (mirrors the detail report so the
// card figures equal what the drill-down shows). Defaults to source code "2".
const DEFAULT_SOURCE_CODE = "2";
// Fixed display order for the expense budget-category (root) cards.
const ROOT_ORDER = ["51000", "52000", "53000", "54000", "55000", "07020"];
// Top-level fund/activity rows shown per card before collapsing the tail.
const BREAKDOWN_MAX = 5;

// Thai status labels + bootstrap badge colours, per document type.
const STATE_LABELS = {
    "budget.commitment": {
        draft: "ร่าง",
        reserved: "จองแล้ว",
        partial: "กำลังดำเนินการ",
        done: "เสร็จสิ้น",
        cancel: "ยกเลิก",
    },
    "budget.move": {
        draft: "ร่าง",
        review: "รอตรวจสอบ",
        posted: "ผ่านรายการ",
        cancel: "ยกเลิก",
    },
    "budget.transfer": {
        draft: "ร่าง",
        submitted: "ส่งอนุมัติ",
        approved: "อนุมัติแล้ว",
        posted: "ผ่านรายการ",
        rejected: "ปฏิเสธ",
        cancelled: "ยกเลิก",
    },
};
const STATE_BADGE = {
    draft: "secondary",
    review: "info",
    submitted: "info",
    reserved: "info",
    partial: "warning",
    approved: "primary",
    posted: "success",
    done: "success",
    cancel: "danger",
    cancelled: "danger",
    rejected: "danger",
};
const MOVE_TYPE_LABELS = {
    entry: "รายการ",
    appropriation: "จัดสรร",
    consume: "ตัดงบ",
};

export class BudgetOverview extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.fiscalYears = [];
        this.sources = [];
        this.departments = [];
        this.state = useState({
            fiscalYearId: false,
            sourceId: false,
            // department (ส่วนงาน) multi-select — defaults to all (no constraint)
            departmentIds: [],
            deptOpen: false,
            hierOp: "=",
            cards: [],
            totals: {},
            sections: [],
            timeseries: {},
            recent: { commitment: [], move: [], transfer: [] },
            loading: false,
        });
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        this.fiscalYears = await this.orm.searchRead(
            "account.fiscal.year",
            [],
            ["id", "name", "date_from", "date_to"],
            { order: "date_from desc" }
        );
        this.sources = await this.orm.searchRead(
            "account.analytic.account",
            [["root_plan_id.code", "=", "sources"]],
            ["id", "display_name", "code"],
            { order: "code" }
        );
        const today = new Date().toISOString().slice(0, 10);
        const covering = this.fiscalYears.find(
            (fy) => fy.date_from <= today && fy.date_to >= today
        );
        this.state.fiscalYearId = (covering || this.fiscalYears[0] || {}).id || false;
        const defSource =
            this.sources.find((s) => s.code === DEFAULT_SOURCE_CODE) || this.sources[0];
        this.state.sourceId = (defSource || {}).id || false;
        // Top-level departments (server decides top-level vs flat). Default all
        // checked — i.e. no constraint until the user narrows the selection.
        this.departments = await this.orm.call(
            "budget.dashboard",
            "get_overview_departments",
            []
        );
        this.state.departmentIds = this.departments.map((d) => d.id);
        await this.load();
    }

    async load() {
        if (!this.state.fiscalYearId) {
            this.state.cards = [];
            return;
        }
        this.state.loading = true;
        try {
            const data = await this.orm.call("budget.dashboard", "get_overview_data", [
                this.state.fiscalYearId,
                this.state.sourceId || false,
                this.departmentParam,
            ]);
            const rank = (code) => {
                const i = ROOT_ORDER.indexOf(code);
                return i === -1 ? ROOT_ORDER.length : i;
            };
            this.state.cards = (data.cards || []).sort(
                (a, b) => rank(a.code) - rank(b.code) || a.code.localeCompare(b.code)
            );
            this.state.totals = data.totals || {};
            this.state.sections = data.sections || [];
            this.state.timeseries = data.timeseries || {};
            this.state.hierOp = data.hier_op || "=";
            this.state.recent = data.recent || { commitment: [], move: [], transfer: [] };
        } finally {
            this.state.loading = false;
        }
    }

    onFiscalYearChange(ev) {
        this.state.fiscalYearId = parseInt(ev.target.value) || false;
        this.load();
    }

    onSourceChange(ev) {
        this.state.sourceId = parseInt(ev.target.value) || false;
        this.load();
    }

    // --- department (ส่วนงาน) multi-select ------------------------------
    get isAllDepartments() {
        return this.state.departmentIds.length === this.departments.length;
    }

    // Filter value sent to the server: ``false`` (no constraint) when all or
    // none are checked, otherwise the explicit subset of department ids.
    get departmentParam() {
        const n = this.state.departmentIds.length;
        if (n === 0 || n === this.departments.length) {
            return false;
        }
        return this.state.departmentIds.slice();
    }

    get departmentLabel() {
        const n = this.state.departmentIds.length;
        if (n === 0 || n === this.departments.length) {
            return "ทั้งหมด";
        }
        return `${n} ส่วนงาน`;
    }

    toggleDeptOpen() {
        this.state.deptOpen = !this.state.deptOpen;
    }

    closeDept() {
        this.state.deptOpen = false;
    }

    toggleDepartment(id) {
        const ids = this.state.departmentIds;
        const i = ids.indexOf(id);
        if (i === -1) {
            ids.push(id);
        } else {
            ids.splice(i, 1);
        }
        this.load();
    }

    selectAllDepartments() {
        this.state.departmentIds = this.departments.map((d) => d.id);
        this.load();
    }

    clearDepartments() {
        this.state.departmentIds = [];
        this.load();
    }

    format(value) {
        return (value || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    // --- card derived values --------------------------------------------
    usedPct(card) {
        if (!card.current || card.current <= 0) {
            return card.used > 0 ? 100 : 0;
        }
        return Math.min(100, Math.max(0, (card.used / card.current) * 100));
    }

    cardStatus(card) {
        // over budget -> danger, near limit -> warning, otherwise ok
        if (card.remaining < -0.005) {
            return "danger";
        }
        if (this.usedPct(card) >= 90) {
            return "warning";
        }
        return "ok";
    }

    pctLabel(obj) {
        return Math.round(this.usedPct(obj)) + "%";
    }

    // A breakdown / section row is drillable when it maps to a real analytic
    // node — not the aggregated "อื่น ๆ" tail (fund/activity id "more", section
    // id false).
    isDrillable(item) {
        return !!item && !!item.id && item.id !== "more";
    }

    // Top-level breakdown rows: show the largest few, fold the rest into
    // an aggregated "อื่น ๆ" row so a card stays bounded but figures still add up.
    breakdownRows(items) {
        if (!items || items.length <= BREAKDOWN_MAX + 1) {
            return items || [];
        }
        const head = items.slice(0, BREAKDOWN_MAX);
        const rest = items.slice(BREAKDOWN_MAX);
        const agg = rest.reduce(
            (a, r) => {
                a.current += r.current;
                a.used += r.used;
                a.remaining += r.remaining;
                return a;
            },
            {
                id: "more",
                code: "",
                name: `อื่น ๆ (${rest.length})`,
                current: 0,
                used: 0,
                remaining: 0,
            }
        );
        return [...head, agg];
    }

    onCardKey(ev, card) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this.openCategory(card);
        }
    }

    // --- recent-movement helpers ----------------------------------------
    stateLabel(model, value) {
        return (STATE_LABELS[model] || {})[value] || value;
    }

    stateBadge(value) {
        return STATE_BADGE[value] || "secondary";
    }

    moveTypeLabel(value) {
        return MOVE_TYPE_LABELS[value] || value;
    }

    // --- navigation ------------------------------------------------------
    openCategory(card) {
        // Drill into the detailed monitoring dashboard, scoped to this
        // category + the same fiscal year / source so figures line up.
        this.actionService.doAction("budget.action_budget_dashboard", {
            additionalContext: {
                default_fiscal_year_id: this.state.fiscalYearId,
                default_root_account_id: card.id,
                default_source_analytic_id: this.state.sourceId || false,
            },
        });
    }

    // Drill a fund / activity breakdown row into the detailed dashboard, scoped
    // to this category + that dimension value (skips the aggregated "อื่น ๆ"
    // row). stopPropagation so the row click doesn't also open the card.
    openBreakdown(card, item, dimKey, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        if (!item || !item.id || item.id === "more") {
            return;
        }
        const context = {
            default_fiscal_year_id: this.state.fiscalYearId,
            default_root_account_id: card.id,
            default_source_analytic_id: this.state.sourceId || false,
            ["default_" + dimKey]: item.id,
        };
        // The detail dashboard's department filter is single-select; carry it
        // over only when exactly one department is in scope.
        if (this.state.departmentIds.length === 1) {
            context.default_department_analytic_id = this.state.departmentIds[0];
        }
        this.actionService.doAction("budget.action_budget_dashboard", {
            additionalContext: context,
        });
    }

    // Department domain leaf for a drill-down, hierarchy-aware (or null when the
    // department filter is "all").
    _deptDrillLeaf() {
        const param = this.departmentParam;
        if (!param) {
            return null;
        }
        const op = this.state.hierOp === "child_of" ? "child_of" : "in";
        return ["department_analytic_id", op, param];
    }

    // Drill a dimension-section row (โครงการ/กิจกรรม, แผนจัดซื้อจัดจ้าง, …) into
    // its commitment lines, scoped to the active filters.
    openSectionItem(section, item, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        if (!item || !item.id) {
            return; // the aggregated "อื่น ๆ" row (id === false)
        }
        const domain = [
            [section.drill_dim, "=", item.id],
            ["state", "=", "posted"],
            ["commitment_id.state", "in", ["reserved", "partial", "done"]],
            ["account_fiscal_year_id", "=", this.state.fiscalYearId],
        ];
        if (this.state.sourceId) {
            domain.push(["source_analytic_id", "=", this.state.sourceId]);
        }
        const dep = this._deptDrillLeaf();
        if (dep) {
            domain.push(dep);
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `${item.code || ""} ${item.name || ""}`.trim(),
            res_model: "budget.commitment.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain,
            target: "current",
        });
    }

    // --- monthly trend (echarts) ----------------------------------------
    get hasTimeseries() {
        const ts = this.state.timeseries || {};
        return ["reserve", "obligate", "consume"].some((k) =>
            (ts[k] || []).some((v) => Math.abs(v) > 0.005)
        );
    }

    _compactNumber(value) {
        const abs = Math.abs(value || 0);
        if (abs >= 1e6) {
            return (value / 1e6).toFixed(1) + "M";
        }
        if (abs >= 1e3) {
            return (value / 1e3).toFixed(0) + "K";
        }
        return String(Math.round(value || 0));
    }

    get timeseriesOption() {
        const ts = this.state.timeseries || {};
        const bar = (name, data, color) => ({
            name,
            type: "bar",
            stack: "usage",
            emphasis: { focus: "series" },
            itemStyle: { color },
            data: data || [],
        });
        return {
            tooltip: {
                trigger: "axis",
                axisPointer: { type: "shadow" },
                valueFormatter: (v) => this.format(v),
            },
            legend: { data: ["จอง", "ผูกพัน", "เบิกจ่าย"], bottom: 0 },
            grid: { left: 8, right: 16, top: 16, bottom: 40, containLabel: true },
            xAxis: { type: "category", data: ts.labels || [] },
            yAxis: {
                type: "value",
                axisLabel: { formatter: (v) => this._compactNumber(v) },
            },
            series: [
                bar("จอง", ts.reserve, "#3b82f6"),
                bar("ผูกพัน", ts.obligate, "#d97706"),
                bar("เบิกจ่าย", ts.consume, "#15803d"),
            ],
        };
    }

    openRecord(model, id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openList(xmlId) {
        this.actionService.doAction(xmlId);
    }
}

BudgetOverview.template = "budget.BudgetOverview";
BudgetOverview.components = { EChart };

registry.category("actions").add("budget_overview", BudgetOverview);
