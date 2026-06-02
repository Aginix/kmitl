/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

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
        this.state = useState({
            fiscalYearId: false,
            sourceId: false,
            cards: [],
            totals: {},
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
            ]);
            const rank = (code) => {
                const i = ROOT_ORDER.indexOf(code);
                return i === -1 ? ROOT_ORDER.length : i;
            };
            this.state.cards = (data.cards || []).sort(
                (a, b) => rank(a.code) - rank(b.code) || a.code.localeCompare(b.code)
            );
            this.state.totals = data.totals || {};
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

registry.category("actions").add("budget_overview", BudgetOverview);
