/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BudgetDashboard } from "@budget/dashboard/budget_dashboard";

// The picker always shows the full nesting (no toggles) so a code can be found
// under the exact ส่วนงาน → กิจกรรม → กองทุน it is allocated to, and a
// reservation pins that whole tuple. A budget code may be allocated to several
// funds, so fund is a nesting level here even though the dashboard omits it.
const PICKER_BREAKDOWN = [
    "department_analytic_id",
    "activity_analytic_id",
    "fund_analytic_id",
];

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

    // The picker's breakdown is fixed (always on, no toggles) — the table always
    // shows the full ส่วนงาน → กิจกรรม → กองทุน → budget-account hierarchy.
    get breakdownList() {
        return PICKER_BREAKDOWN;
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
            const breakdown = this.breakdownList;
            const data = await this.orm.call(
                "budget.dashboard",
                "get_reservation_grid",
                [
                    this.state.fiscalYearId,
                    this.effectiveFilters,
                    this.state.rootAccountId || false,
                    this.accountDomain,
                    breakdown.length ? breakdown : false,
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
    // Dimensions being broken down are taken from the picked row, so they are no
    // longer required filters.
    get missingDimensions() {
        const fromRow = new Set(this.breakdownList);
        const missing = [];
        for (const dim of this.hierDimensions) {
            if (fromRow.has(dim.key)) {
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
        // Dimension (breakdown) group rows are display-only — tint them apart,
        // shaded per nesting depth.
        if (row.row_type === "dim") {
            parts.push("o_bd_dim", "o_bd_dim_" + (row.dim_level || 0));
        }
        // Pointer affordance + selected highlight only on selectable rows; keyed
        // by row.key so a dimension row never matches a selected account row.
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

    // The breakdown-dimension tuples across the currently-picked rows, as a
    // signature -> {field: id} map. A reservation maps to ONE tuple; confirm()
    // enforces a single, fully-specified tuple. The header-level engine (cap,
    // obligate/consume copying the header distribution) cannot represent a
    // reservation that spans several tuples.
    _pickedTuples() {
        const byKey = this.rowsByKey;
        const fields = this.breakdownList;
        const keys = this.selectMode
            ? this.state.selectedId
                ? [this.state.selectedId]
                : []
            : Object.keys(this.state.amounts).filter(
                  (key) => this.state.amounts[key] > 0
              );
        const tuples = new Map();
        for (const key of keys) {
            const row = byKey[key];
            if (!row) {
                continue;
            }
            const tuple = {};
            let sig = "";
            for (const field of fields) {
                const id = (row.dims && row.dims[field]) || false;
                tuple[field] = id;
                sig += field + ":" + id + "|";
            }
            tuples.set(sig, tuple);
        }
        return tuples;
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

    // The reservation's analytic_distribution: filter-bar dimensions, except that
    // every dimension being broken down is taken from the single picked tuple
    // (the picked rows share one tuple, enforced in confirm()), not the filter.
    get selectedDistribution() {
        const fields = this.breakdownList;
        const fromRow = new Set(fields);
        const dist = {};
        for (const [key, value] of Object.entries(this.effectiveFilters)) {
            if (fromRow.has(key) || !value) {
                continue;
            }
            dist[value] = 100.0;
        }
        const tuples = this._pickedTuples();
        if (tuples.size === 1) {
            const tuple = [...tuples.values()][0];
            for (const field of fields) {
                if (tuple[field]) {
                    dist[tuple[field]] = 100.0;
                }
            }
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
        // The broken-down dimensions come from the picked rows; a reservation maps
        // to a single fully-specified tuple, so reject picks under a "ไม่ระบุ"
        // sentinel or spanning more than one tuple (the engine cannot represent
        // a multi-tuple reservation).
        const fields = this.breakdownList;
        if (fields.length) {
            const tuples = this._pickedTuples();
            if (tuples.size > 1) {
                this.notification.add(
                    "เลือกรหัสได้ทีละชุดมิติ (ส่วนงาน/กิจกรรม/กองทุนเดียวกัน) เท่านั้น",
                    { type: "warning" }
                );
                return;
            }
            const tuple = tuples.size === 1 ? [...tuples.values()][0] : {};
            if (!tuples.size || fields.some((field) => !tuple[field])) {
                this.notification.add(
                    "กรุณาเลือกรหัสที่ระบุ ส่วนงาน/กิจกรรม/กองทุน ครบ (ไม่ใช่แถว 'ไม่ระบุ')",
                    { type: "warning" }
                );
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
