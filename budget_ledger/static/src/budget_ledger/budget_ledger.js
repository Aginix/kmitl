/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

// kind → Thai label + css modifier (colour lives in the SCSS).
const KIND_META = {
    appropriation: { label: "จัดสรร", cls: "o_bl_k_appr" },
    transfer_in: { label: "รับโอน", cls: "o_bl_k_tin" },
    transfer_out: { label: "โอนออก", cls: "o_bl_k_tout" },
    consume: { label: "เบิกจ่าย", cls: "o_bl_k_cons" },
};

// The six dimension chips, in display order. `key` matches row.dims keys.
const DIM_META = [
    { key: "department", label: "ส่วนงาน" },
    { key: "source", label: "แหล่งเงิน" },
    { key: "fund", label: "กองทุน" },
    { key: "activity", label: "กิจกรรม" },
    { key: "kmitl_project", label: "โครงการ/กิจกรรม" },
    { key: "procurement_plan", label: "แผนจัดซื้อจัดจ้าง" },
];

// One multi-select dropdown per dimension. `field` matches the backend filter.
const DIM_FILTERS = [
    { field: "department_analytic_id", label: "ส่วนงาน" },
    { field: "source_analytic_id", label: "แหล่งเงิน" },
    { field: "fund_analytic_id", label: "กองทุน" },
    { field: "activity_analytic_id", label: "กิจกรรม" },
    { field: "kmitl_project_analytic_id", label: "โครงการ/กิจกรรม" },
    { field: "procurement_plan_analytic_id", label: "แผนจัดซื้อจัดจ้าง" },
];

export class BudgetLedger extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dimFilters = DIM_FILTERS;
        this.dimMeta = DIM_META;
        this.state = useState({
            fiscalYears: [],
            dims: {}, // field -> [{id, display_name, code}]
            accounts: [],
            fiscalYearId: false,
            budgetType: "expense",
            kinds: { appropriation: true, transfer: true, consume: true },
            dimSelections: {}, // field -> [ids]
            accountId: false,
            includeDraft: false,
            openDropdown: null,
            summary: {},
            months: [],
            expanded: {},
            collapsedMonths: {},
            loading: false,
        });
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        const opts = await this.orm.call("budget.ledger", "get_filter_options", []);
        this.state.fiscalYears = opts.fiscal_years || [];
        this.state.dims = opts.dims || {};
        this.state.accounts = opts.accounts || [];
        for (const dim of DIM_FILTERS) {
            this.state.dimSelections[dim.field] = [];
        }
        const today = new Date().toISOString().slice(0, 10);
        const covering = this.state.fiscalYears.find(
            (fy) => fy.date_from <= today && fy.date_to >= today
        );
        this.state.fiscalYearId =
            (covering || this.state.fiscalYears[0] || {}).id || false;
        await this.load();
    }

    async load() {
        if (!this.state.fiscalYearId) {
            this.state.months = [];
            this.state.summary = {};
            return;
        }
        this.state.loading = true;
        try {
            const filters = {};
            for (const dim of DIM_FILTERS) {
                const ids = this.state.dimSelections[dim.field] || [];
                if (ids.length) {
                    filters[dim.field] = ids.slice();
                }
            }
            if (this.state.accountId) {
                filters.account_id = this.state.accountId;
            }
            const kinds = Object.keys(this.state.kinds).filter(
                (k) => this.state.kinds[k]
            );
            const data = await this.orm.call("budget.ledger", "get_ledger_data", [
                this.state.fiscalYearId,
                {
                    budget_type: this.state.budgetType,
                    filters,
                    kinds,
                    include_draft: this.state.includeDraft,
                },
            ]);
            this.state.summary = data.summary || {};
            this.state.months = data.months || [];
            this.state.expanded = {};
        } finally {
            this.state.loading = false;
        }
    }

    // --- filter handlers -------------------------------------------------
    onFiscalYearChange(ev) {
        this.state.fiscalYearId = parseInt(ev.target.value) || false;
        this.load();
    }
    setBudgetType(bt) {
        if (this.state.budgetType !== bt) {
            this.state.budgetType = bt;
            this.load();
        }
    }
    toggleKind(k) {
        this.state.kinds[k] = !this.state.kinds[k];
        this.load();
    }
    onAccountChange(ev) {
        this.state.accountId = parseInt(ev.target.value) || false;
        this.load();
    }
    toggleDraft() {
        this.state.includeDraft = !this.state.includeDraft;
        this.load();
    }

    // --- dimension multi-select dropdown --------------------------------
    toggleDropdown(field) {
        this.state.openDropdown =
            this.state.openDropdown === field ? null : field;
    }
    closeDropdown() {
        this.state.openDropdown = null;
    }
    isDimChecked(field, id) {
        return (this.state.dimSelections[field] || []).includes(id);
    }
    toggleDim(field, id) {
        const arr =
            this.state.dimSelections[field] ||
            (this.state.dimSelections[field] = []);
        const i = arr.indexOf(id);
        if (i === -1) {
            arr.push(id);
        } else {
            arr.splice(i, 1);
        }
        this.load();
    }
    clearDim(field) {
        this.state.dimSelections[field] = [];
        this.load();
    }
    dimLabel(field) {
        const n = (this.state.dimSelections[field] || []).length;
        return n === 0 ? "ทั้งหมด" : `${n} รายการ`;
    }

    // --- month collapse + row expand ------------------------------------
    toggleMonth(key) {
        this.state.collapsedMonths[key] = !this.state.collapsedMonths[key];
    }
    isMonthCollapsed(key) {
        return !!this.state.collapsedMonths[key];
    }
    toggleRow(id) {
        this.state.expanded[id] = !this.state.expanded[id];
    }
    isExpanded(id) {
        return !!this.state.expanded[id];
    }

    // --- display helpers -------------------------------------------------
    format(v) {
        return (v || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
    signed(v) {
        const s = this.format(Math.abs(v || 0));
        return (v || 0) >= 0 ? "+" + s : "-" + s;
    }
    kindClass(k) {
        return (KIND_META[k] || {}).cls || "";
    }
    // Non-empty dimension chips for a row (empty / filtered-out dims hide).
    dimEntries(row) {
        return DIM_META.map((d) => ({
            label: d.label,
            value: row.dims[d.key],
        })).filter((e) => e.value);
    }
    hasSummary() {
        return (
            this.state.summary && this.state.summary.current !== undefined
        );
    }

    openSource(row) {
        if (!row.source_model || !row.source_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: row.source_model,
            res_id: row.source_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    openMove(row) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "budget.move",
            res_id: row.move_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

BudgetLedger.template = "budget_ledger.BudgetLedger";

registry.category("actions").add("budget_ledger", BudgetLedger);
