/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

// Reservation picker (จองงบประมาณ): shows the budget.account hierarchy with the
// control-node available per budgetable row for the commitment's FIXED
// dimension combination, and lets the user enter the amount to reserve on the
// far-right column. Normally one budget code; multiple are allowed only when
// every code is cross_chargeable (the backend constraint enforces it).
//
// Opened as a client action (target:"new") from the budget.commitment form,
// mirroring action_view_budget_dashboard. On confirm it writes reserve lines
// via budget.commitment.apply_reservation_selection.
export class BudgetReservationPicker extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        const ctx = (this.props.action && this.props.action.context) || {};
        this.commitmentId = ctx.commitment_id;
        this.fiscalYearId = ctx.fiscal_year_id || false;
        this.analyticDistribution = ctx.analytic_distribution || {};

        this.state = useState({
            rows: [],
            amounts: {}, // { [accountId]: number }
            collapsed: {},
            loading: false,
            currencyId: false,
        });
        onWillStart(this.load.bind(this));
    }

    async load() {
        if (!this.fiscalYearId) {
            this.state.rows = [];
            return;
        }
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "budget.dashboard",
                "get_reservation_grid",
                [this.fiscalYearId, this.analyticDistribution, false]
            );
            this.state.rows = data.rows || [];
            this.state.currencyId = data.currency_id;
        } finally {
            this.state.loading = false;
        }
    }

    get rowsById() {
        const byId = {};
        for (const row of this.state.rows) {
            byId[row.id] = row;
        }
        return byId;
    }

    // Hide rows whose ancestor is collapsed (same logic as the dashboard).
    get visibleRows() {
        const byId = this.rowsById;
        const collapsed = this.state.collapsed;
        const hidden = (row) => {
            let pid = row.parent_id;
            while (pid) {
                if (collapsed[pid]) {
                    return true;
                }
                pid = byId[pid] ? byId[pid].parent_id : false;
            }
            return false;
        };
        return this.state.rows.filter((row) => !hidden(row));
    }

    toggleRow(row) {
        if (row.has_children) {
            this.state.collapsed[row.id] = !this.state.collapsed[row.id];
        }
    }

    onAmountInput(row, ev) {
        const value = parseFloat(ev.target.value);
        if (value > 0) {
            this.state.amounts[row.id] = value;
        } else {
            delete this.state.amounts[row.id];
        }
    }

    entered(row) {
        return this.state.amounts[row.id] || 0;
    }

    // A row is over budget when its entered amount exceeds its available.
    isOver(row) {
        const amount = this.entered(row);
        return (
            amount > 0 &&
            row.available !== null &&
            amount > (row.available || 0) + 0.005
        );
    }

    get selections() {
        return Object.entries(this.state.amounts)
            .filter(([, amount]) => amount > 0)
            .map(([id, amount]) => ({ account_id: parseInt(id), amount }));
    }

    get hasBlocking() {
        return this.state.rows.some((row) => this.isOver(row));
    }

    format(value) {
        return (value || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    async confirm() {
        if (!this.selections.length) {
            this.notification.add("กรุณาระบุงบประมาณอย่างน้อย 1 รหัส", {
                type: "warning",
            });
            return;
        }
        if (this.hasBlocking) {
            this.notification.add("มีรหัสงบประมาณที่ยอดเกินงบคงเหลือ", {
                type: "danger",
            });
            return;
        }
        // Lets the backend cross-charge / availability constraints raise to the
        // user (caught and shown by the web client).
        await this.orm.call("budget.commitment", "apply_reservation_selection", [
            [this.commitmentId],
            this.selections,
        ]);
        this.close();
    }

    close() {
        // Close the picker dialog. This client action is launched from a
        // type="object" form button, so Odoo's doActionButton reloads the
        // commitment form when the dialog closes (the same mechanism the
        // obligate/consume wizards rely on) — the new reserve lines then show.
        this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }
}

BudgetReservationPicker.template = "budget.BudgetReservationPicker";

registry.category("actions").add("budget_reservation_picker", BudgetReservationPicker);
