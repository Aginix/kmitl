/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BudgetDashboard } from "@budget/dashboard/budget_dashboard";

// Reservation picker (จองงบประมาณ): the monitoring dashboard made selectable.
// Extends BudgetDashboard so it reuses the filter bar (dimensions chosen here),
// the full columns, and the hierarchy. Clicking a row selects that budget code.
// Host-agnostic via context (res_model/res_id/select_only/account_domain); on
// confirm it calls <res_model>.apply_reservation_selection(selections, dims).
//   select_only=true  (PR/PO/DR): pick one code -> writes budget_account_id + dims
//   select_only=false (budget.commitment): per-row amount -> reserve lines
export class BudgetReservationPicker extends BudgetDashboard {
    setup() {
        super.setup();
        this.notification = useService("notification");
        const ctx = (this.props.action && this.props.action.context) || {};
        this.resModel = ctx.res_model;
        this.resId = ctx.res_id;
        this.selectMode = !!ctx.select_only;
        this.accountDomain = ctx.account_domain || false;
        this.state.selectedId = false;
        this.state.amounts = {};
    }

    // Use the picker feed: same dashboard columns + budgetable/selectable flags.
    async load() {
        if (!this.state.fiscalYearId) {
            this.state.rows = [];
            return;
        }
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "budget.dashboard",
                "get_reservation_grid",
                [
                    this.state.fiscalYearId,
                    this.effectiveFilters,
                    this.state.rootAccountId || false,
                    this.accountDomain,
                ]
            );
            this.state.rows = data.rows || [];
            this.state.hierOp = data.hier_op || "=";
        } finally {
            this.state.loading = false;
        }
    }

    // Clicking anywhere on a row selects it (select mode). Toggles off if clicked
    // again. Non-selectable rows (rollups / out-of-domain) do nothing.
    onRowClick(row) {
        if (this.selectMode && row.selectable) {
            this.state.selectedId =
                this.state.selectedId === row.id ? false : row.id;
        }
    }

    // The dashboard wires figure cells to drill actions; in the picker every
    // click just selects the row.
    drillBudget(row) {
        this.onRowClick(row);
    }
    drillUsage(row) {
        this.onRowClick(row);
    }

    rowClass(row) {
        const parts = [];
        if (row.has_children) {
            parts.push("o_bd_group");
        }
        if (this.state.selectedId === row.id) {
            parts.push("o_brp_selected");
        }
        return parts.join(" ");
    }

    onAmountInput(row, ev) {
        const value = parseFloat(ev.target.value);
        if (value > 0) {
            this.state.amounts[row.id] = value;
        } else {
            delete this.state.amounts[row.id];
        }
    }

    get selections() {
        if (this.selectMode) {
            return this.state.selectedId
                ? [{ account_id: this.state.selectedId }]
                : [];
        }
        return Object.entries(this.state.amounts)
            .filter(([, amount]) => amount > 0)
            .map(([id, amount]) => ({ account_id: parseInt(id), amount }));
    }

    // The dimension combination chosen in the filter bar -> analytic_distribution.
    get selectedDistribution() {
        const dist = {};
        for (const value of Object.values(this.effectiveFilters)) {
            if (value) {
                dist[value] = 100.0;
            }
        }
        return dist;
    }

    async confirm() {
        if (!this.selections.length) {
            this.notification.add("กรุณาเลือกงบประมาณ", { type: "warning" });
            return;
        }
        // The host's apply_reservation_selection writes back; its cross-charge /
        // single-code / domain constraints raise to the user.
        await this.orm.call(this.resModel, "apply_reservation_selection", [
            [this.resId],
            this.selections,
            this.selectedDistribution,
        ]);
        this.close();
    }

    close() {
        // Launched from a type="object" form button, so Odoo reloads the host
        // form when this dialog closes (same mechanism as the obligate/consume
        // wizards) — the new selection then shows.
        this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }
}

BudgetReservationPicker.template = "budget.BudgetReservationPicker";

registry.category("actions").add("budget_reservation_picker", BudgetReservationPicker);
