/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";

const PLAN_MODEL = "budget.expense.plan";
const OVERVIEW = "overview";

export class ExpensePlanGrid extends Component {
    setup() {
        useSubEnv({ config: { ...getDefaultConfig(), ...this.env.config } });
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.planId =
            this.props.action.params?.plan_id ||
            this.props.action.context?.active_id ||
            false;
        this.state = useState({
            data: { rows: [], months: [], chosen_activities: [], available_activities: [] },
            loading: false,
            showActual: true,
            view: OVERVIEW, // OVERVIEW or a template_activity_id
            dirty: {}, // "aId|fId|blId|month" -> amount
        });
        onWillStart(this.load.bind(this));
    }

    async load() {
        if (!this.planId) {
            return;
        }
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(PLAN_MODEL, "get_grid_data", [
                this.planId,
            ]);
            this.state.dirty = {};
            // keep the active view valid
            const ids = this.state.data.chosen_activities.map((a) => a.id);
            if (this.state.view !== OVERVIEW && !ids.includes(this.state.view)) {
                this.state.view = OVERVIEW;
            }
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------ views
    get isOverview() {
        return this.state.view === OVERVIEW;
    }
    get isEditable() {
        return this.state.data.editable && !this.isOverview;
    }
    selectActivity(id) {
        this.state.view = id;
    }
    showOverview() {
        this.state.view = OVERVIEW;
    }

    // Rows for the current view: aggregated across activities (overview) or the
    // selected activity's own rows.
    get currentRows() {
        const months = this.state.data.months;
        if (this.isOverview) {
            const byKey = new Map();
            const order = [];
            for (const r of this.state.data.rows) {
                const k = `${r.fund_id}|${r.budget_line_id}`;
                let row = byKey.get(k);
                if (!row) {
                    row = {
                        fund_id: r.fund_id,
                        fund_name: r.fund_name,
                        budget_line_id: r.budget_line_id,
                        budget_line_name: r.budget_line_name,
                        category_name: r.category_name,
                        plan: {},
                        actual: {},
                    };
                    byKey.set(k, row);
                    order.push(row);
                }
                for (const mo of months) {
                    row.plan[mo.m] = (row.plan[mo.m] || 0) + (r.plan[mo.m] || 0);
                    row.actual[mo.m] = (row.actual[mo.m] || 0) + (r.actual[mo.m] || 0);
                }
            }
            return order;
        }
        return this.state.data.rows.filter((r) => r.template_activity_id === this.state.view);
    }

    // Group current rows by fund (same fund kept together).
    get fundGroups() {
        const groups = [];
        let current = null;
        for (const row of this.currentRows) {
            if (!current || current.fund_id !== row.fund_id) {
                current = { fund_id: row.fund_id, fund_name: row.fund_name, rows: [] };
                groups.push(current);
            }
            current.rows.push(row);
        }
        return groups;
    }

    // ------------------------------------------------------------------ editing
    get isDirty() {
        return Object.keys(this.state.dirty).length > 0;
    }
    onAmountInput(row, month, ev) {
        const value = this.parseAmount(ev.target.value);
        row.plan[month] = value;
        // key by the row's analytic activity id (what set_amounts stores); only
        // reachable in per-activity edit mode where rows carry activity_id.
        this.state.dirty[
            `${row.activity_id}|${row.fund_id}|${row.budget_line_id}|${month}`
        ] = value;
    }
    async save() {
        if (!this.isDirty) {
            return;
        }
        const changes = Object.entries(this.state.dirty).map(([k, amount]) => {
            const [activity_id, fund_id, budget_line_id, month] = k.split("|");
            return {
                activity_id: parseInt(activity_id),
                fund_id: parseInt(fund_id),
                budget_line_id: parseInt(budget_line_id),
                month: parseInt(month),
                amount,
            };
        });
        this.state.loading = true;
        try {
            await this.orm.call(PLAN_MODEL, "set_amounts", [this.planId, changes]);
            this.notification.add(_t("บันทึกแผนแล้ว"), { type: "success" });
            await this.load();
        } finally {
            this.state.loading = false;
        }
    }
    async discard() {
        await this.load();
    }

    // ------------------------------------------------------------------ activities
    async addActivity(ev) {
        const taId = parseInt(ev.target.value);
        if (!taId) {
            return;
        }
        ev.target.value = "";
        await this.orm.call(PLAN_MODEL, "add_activity", [this.planId, taId]);
        await this.load();
        this.state.view = taId; // jump into the newly added activity to fill it
    }
    async removeActivity(templateActivityId) {
        if (this.state.view === templateActivityId) {
            this.state.view = OVERVIEW;
        }
        await this.orm.call(PLAN_MODEL, "remove_activity", [this.planId, templateActivityId]);
        await this.load();
    }

    // ------------------------------------------------------------------ totals + format
    rowTotal(row, which) {
        return this.state.data.months.reduce((s, mo) => s + (row[which][mo.m] || 0), 0);
    }
    monthTotal(month, which) {
        return this.currentRows.reduce((s, row) => s + (row[which][month] || 0), 0);
    }
    grandTotal(which) {
        return this.currentRows.reduce((s, row) => s + this.rowTotal(row, which), 0);
    }
    formatAmount(value) {
        return (value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
    formatInput(value) {
        return value
            ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
            : "";
    }
    parseAmount(str) {
        return parseFloat(String(str).replace(/,/g, "")) || 0.0;
    }

    async exportXlsx() {
        await this.action.doAction({
            type: "ir.actions.report",
            report_type: "xlsx",
            report_name: "budget_expense_plan.expense_plan_xlsx",
            report_file: "budget_expense_plan.expense_plan_xlsx",
            model: PLAN_MODEL,
            context: { active_ids: [this.planId], active_id: this.planId },
        });
    }
}

ExpensePlanGrid.template = "budget_expense_plan.ExpensePlanGrid";
ExpensePlanGrid.components = { Layout };

registry.category("actions").add("budget_expense_plan_grid", ExpensePlanGrid);
