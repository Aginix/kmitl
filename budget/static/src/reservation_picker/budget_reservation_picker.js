/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

// Reservation picker (จองงบประมาณ): the budget.account hierarchy with the
// control-node available per budgetable row for a FIXED dimension combination.
// Host-agnostic — driven entirely by context:
//   res_model / res_id          the document to write back to
//   fiscal_year_id              scopes availability
//   analytic_distribution       the fixed dimension combination
//   root_account_id             optional subtree to show
//   select_only                 true on hosts that carry a single budget code
//                               (PR/PO/DR) -> pick one row; false on
//                               budget.commitment -> enter amount(s) -> lines
// On confirm it calls <res_model>.apply_reservation_selection(selections).
export class BudgetReservationPicker extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        const ctx = (this.props.action && this.props.action.context) || {};
        this.resModel = ctx.res_model;
        this.resId = ctx.res_id;
        this.fiscalYearId = ctx.fiscal_year_id || false;
        this.analyticDistribution = ctx.analytic_distribution || {};
        this.rootAccountId = ctx.root_account_id || false;
        this.accountDomain = ctx.account_domain || false;
        this.selectMode = !!ctx.select_only;

        this.state = useState({
            rows: [],
            amounts: {}, // amount mode: { [accountId]: number }
            selectedId: false, // select mode: a single account id
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
                [
                    this.fiscalYearId,
                    this.analyticDistribution,
                    this.rootAccountId,
                    this.accountDomain,
                ]
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

    // --- select mode ---
    selectRow(row) {
        if (row.selectable) {
            this.state.selectedId = row.id;
        }
    }

    // --- amount mode ---
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
        if (this.selectMode) {
            return this.state.selectedId
                ? [{ account_id: this.state.selectedId }]
                : [];
        }
        return Object.entries(this.state.amounts)
            .filter(([, amount]) => amount > 0)
            .map(([id, amount]) => ({ account_id: parseInt(id), amount }));
    }

    get hasBlocking() {
        return !this.selectMode && this.state.rows.some((row) => this.isOver(row));
    }

    format(value) {
        return (value || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    async confirm() {
        if (!this.selections.length) {
            this.notification.add("กรุณาเลือกงบประมาณอย่างน้อย 1 รหัส", {
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
        // The host's apply_reservation_selection performs the write; its
        // cross-charge / single-code / availability constraints raise to the
        // user (the web client surfaces them).
        await this.orm.call(this.resModel, "apply_reservation_selection", [
            [this.resId],
            this.selections,
        ]);
        this.close();
    }

    close() {
        // Close the picker dialog. This client action is launched from a
        // type="object" form button, so Odoo's doActionButton reloads the host
        // form when the dialog closes (the same mechanism the obligate/consume
        // wizards rely on) — the new selection then shows.
        this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }
}

BudgetReservationPicker.template = "budget.BudgetReservationPicker";

registry.category("actions").add("budget_reservation_picker", BudgetReservationPicker);
