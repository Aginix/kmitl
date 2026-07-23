/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";

const PLAN_MODEL = "budget.expense.plan";

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
            data: { rows: [], months: [], available_activities: [] },
            loading: false,
            showActual: true,
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
        } finally {
            this.state.loading = false;
        }
    }

    get isDirty() {
        return Object.keys(this.state.dirty).length > 0;
    }

    key(row, month) {
        return `${row.activity_id}|${row.fund_id}|${row.budget_line_id}|${month}`;
    }

    // ------------------------------------------------------------------
    // Editing
    // ------------------------------------------------------------------
    onAmountInput(row, month, ev) {
        const value = parseFloat(ev.target.value) || 0.0;
        row.plan[month] = value;
        this.state.dirty[this.key(row, month)] = value;
    }

    async save() {
        if (!this.isDirty) {
            return;
        }
        const changes = Object.entries(this.state.dirty).map(([key, amount]) => {
            const [activity_id, fund_id, budget_line_id, month] = key.split("|");
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

    // ------------------------------------------------------------------
    // Activity selection (the unit chooses its own activities)
    // ------------------------------------------------------------------
    async addActivity(ev) {
        const taId = parseInt(ev.target.value);
        if (!taId) {
            return;
        }
        ev.target.value = "";
        await this.orm.call(PLAN_MODEL, "add_activity", [this.planId, taId]);
        await this.load();
    }

    async removeActivity(templateActivityId) {
        await this.orm.call(PLAN_MODEL, "remove_activity", [
            this.planId,
            templateActivityId,
        ]);
        await this.load();
    }

    // ------------------------------------------------------------------
    // Rendering helpers
    // ------------------------------------------------------------------
    get groups() {
        const groups = [];
        let current = null;
        for (const row of this.state.data.rows) {
            if (!current || current.template_activity_id !== row.template_activity_id) {
                current = {
                    template_activity_id: row.template_activity_id,
                    activity_name: row.activity_name,
                    rows: [],
                };
                groups.push(current);
            }
            current.rows.push(row);
        }
        return groups;
    }

    rowTotal(row, which) {
        return this.state.data.months.reduce(
            (sum, mo) => sum + (row[which][mo.m] || 0.0),
            0.0
        );
    }

    monthTotal(month, which) {
        return this.state.data.rows.reduce(
            (sum, row) => sum + (row[which][month] || 0.0),
            0.0
        );
    }

    grandTotal(which) {
        return this.state.data.rows.reduce(
            (sum, row) => sum + this.rowTotal(row, which),
            0.0
        );
    }

    formatAmount(value) {
        if (!value) {
            return "0.00";
        }
        return value.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
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
