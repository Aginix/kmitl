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
            data: { rows: [], months: [] },
            loading: false,
            showActual: true,
            dirty: {}, // "tlId|month" -> amount
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

    // ------------------------------------------------------------------
    // Editing
    // ------------------------------------------------------------------
    onAmountInput(row, month, ev) {
        const value = parseFloat(ev.target.value) || 0.0;
        row.plan[month] = value;
        this.state.dirty[`${row.template_line_id}|${month}`] = value;
    }

    async save() {
        if (!this.isDirty) {
            return;
        }
        const changes = Object.entries(this.state.dirty).map(([key, amount]) => {
            const [tlId, month] = key.split("|");
            return {
                template_line_id: parseInt(tlId),
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

    // ------------------------------------------------------------------
    // Rendering helpers
    // ------------------------------------------------------------------
    get groups() {
        // Group rows by Activity for section rendering, preserving row order.
        const groups = [];
        let current = null;
        for (const row of this.state.data.rows) {
            if (!current || current.activity_id !== row.activity_id) {
                current = {
                    activity_id: row.activity_id,
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
}

ExpensePlanGrid.template = "budget_expense_plan.ExpensePlanGrid";
ExpensePlanGrid.components = { Layout };

registry.category("actions").add("budget_expense_plan_grid", ExpensePlanGrid);
