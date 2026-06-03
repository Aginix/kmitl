/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BudgetDashboard } from "@budget/dashboard/budget_dashboard";

// The activity dimension field; in breakdown mode its value is sourced from the
// picked row's hierarchy rather than the filter bar.
const ACTIVITY_KEY = "activity_analytic_id";

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
        // Reservations pick a specific activity, so show the breakdown by default.
        this.state.groupByActivity = true;
    }

    // Use the picker feed: same dashboard columns + budgetable/selectable flags.
    // Any filter change reloads the grid, so clear the prior selection here —
    // the chosen row/amount no longer maps to the new filter combination.
    async load() {
        this.state.selectedId = false;
        this.state.amounts = {};
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
                    this.state.groupByActivity ? "activity_analytic_id" : false,
                ]
            );
            this.state.rows = data.rows || [];
            this.state.hierOp = data.hier_op || "=";
        } finally {
            this.state.loading = false;
        }
    }

    // A reservation needs a SPECIFIC value per dimension — drop the
    // "— ทั้งหมด —" (all) option the dashboard offers for aggregate views.
    sourcesFor(dim) {
        const [src] = super.sourcesFor(dim);
        return [
            {
                options: async (request) => {
                    const opts = await src.options(request);
                    return opts.filter((o) => o.accountId);
                },
            },
        ];
    }

    async onWillStart() {
        await super.onWillStart();
        // Force a single budget category (no "all") — default to the first.
        if (!this.state.rootAccountId && this.rootAccounts.length) {
            this.state.rootAccountId = this.rootAccounts[0].id;
            await this.load();
        }
    }

    // Dimensions the reservation still needs (the filter bar must be complete).
    // In the activity breakdown the activity is taken from the picked row, so it
    // is no longer a required filter.
    get missingDimensions() {
        const missing = [];
        for (const dim of this.hierDimensions) {
            if (dim.key === ACTIVITY_KEY && this.state.groupByActivity) {
                continue;
            }
            if (!this.state.filters[dim.key]) {
                missing.push(dim.label);
            }
        }
        if (!this.state.sourceId) {
            missing.push("แหล่งเงิน");
        }
        return missing;
    }

    // Clicking anywhere on a row selects it (select mode). Toggles off if clicked
    // again. Non-selectable rows (rollups, activity group rows, out-of-domain)
    // do nothing. Keyed by row.key, not the account id: in the activity
    // breakdown the same account can appear under several activities, and each
    // displayed row must select independently.
    onRowClick(row) {
        if (this.selectMode && row.selectable) {
            this.state.selectedId =
                this.state.selectedId === row.key ? false : row.key;
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
        // Activity (breakdown) group rows are display-only — tint them apart.
        if (row.row_type === "activity") {
            parts.push("o_bd_activity");
        }
        // Pointer affordance + selected highlight only on selectable rows; keyed
        // by row.key so an activity row (key "a<id>") never matches a selected
        // account row (key "a<id>-b<id>").
        if (row.selectable) {
            parts.push("o_brp_selectable");
        }
        if (this.state.selectedId === row.key) {
            parts.push("o_brp_selected");
        }
        return parts.join(" ");
    }

    onAmountInput(row, ev) {
        const value = parseFloat(ev.target.value);
        if (value > 0) {
            this.state.amounts[row.key] = value;
        } else {
            delete this.state.amounts[row.key];
        }
    }

    // Distinct activities across the currently-picked rows (false = the
    // "ไม่ระบุ" sentinel / no activity). A reservation maps to ONE activity, so
    // confirm() enforces this resolves to a single real activity in breakdown
    // mode; the rest of the engine (cap, obligate/consume) is header-level.
    _pickedActivityIds() {
        const byKey = this.rowsByKey;
        const keys = this.selectMode
            ? this.state.selectedId
                ? [this.state.selectedId]
                : []
            : Object.keys(this.state.amounts).filter(
                  (key) => this.state.amounts[key] > 0
              );
        const ids = new Set();
        for (const key of keys) {
            const row = byKey[key];
            if (row) {
                ids.add(row.activity_id || false);
            }
        }
        return ids;
    }

    get selections() {
        const byKey = this.rowsByKey;
        if (this.selectMode) {
            const row = this.state.selectedId && byKey[this.state.selectedId];
            return row ? [{ account_id: row.account_id }] : [];
        }
        // One reserve line per budget account (the single reservation activity is
        // carried by the shared distribution); fold duplicate rows of the same
        // account together.
        const byAccount = {};
        for (const [key, amount] of Object.entries(this.state.amounts)) {
            const row = byKey[key];
            if (!row || !(amount > 0)) {
                continue;
            }
            byAccount[row.account_id] = (byAccount[row.account_id] || 0) + amount;
        }
        return Object.entries(byAccount).map(([id, amount]) => ({
            account_id: parseInt(id),
            amount,
        }));
    }

    // The reservation's analytic_distribution: filter-bar dimensions, but with the
    // ACTIVITY taken from the picked row's hierarchy in breakdown mode (the picked
    // rows share one activity, enforced in confirm()), not the filter bar.
    get selectedDistribution() {
        const dist = {};
        for (const [key, value] of Object.entries(this.effectiveFilters)) {
            if (key === ACTIVITY_KEY || !value) {
                continue;
            }
            dist[value] = 100.0;
        }
        let activityId = this.effectiveFilters[ACTIVITY_KEY];
        if (this.state.groupByActivity) {
            const ids = this._pickedActivityIds();
            activityId = ids.size === 1 ? [...ids][0] : false;
        }
        if (activityId) {
            dist[activityId] = 100.0;
        }
        return dist;
    }

    async confirm() {
        const missing = this.missingDimensions;
        if (missing.length) {
            this.notification.add("กรุณาเลือกมิติให้ครบก่อน: " + missing.join(", "), {
                type: "warning",
            });
            return;
        }
        if (!this.selections.length) {
            this.notification.add("กรุณาเลือกงบประมาณ", { type: "warning" });
            return;
        }
        // In breakdown mode the activity comes from the picked rows; a reservation
        // maps to a single activity, so reject the "ไม่ระบุ" sentinel and picks
        // that span more than one activity (which the engine cannot represent).
        if (this.state.groupByActivity) {
            const ids = this._pickedActivityIds();
            if (!ids.size || ids.has(false)) {
                this.notification.add(
                    "กรุณาเลือกรหัสที่อยู่ภายใต้กิจกรรม (ไม่ใช่แถว 'ไม่ระบุ')",
                    { type: "warning" }
                );
                return;
            }
            if (ids.size > 1) {
                this.notification.add("เลือกรหัสได้ทีละกิจกรรมเท่านั้น", {
                    type: "warning",
                });
                return;
            }
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
