/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BudgetDashboard } from "@budget/dashboard/budget_dashboard";
import { BudgetOverview } from "@budget/overview/budget_overview";

// Usage cells drill into the budget ledger (ADR-0016): each band is exactly the
// negated Σ balance of its bucket, so the list now totals the cell.
const USAGE_LABELS = { reserve: "เงินจอง", obligate: "ผูกพัน", consume: "เบิกจ่าย" };

patch(BudgetDashboard.prototype, "budget_ledger.BudgetDashboard", {
    drillUsage(row, moveType) {
        const domain = [
            ["parent_state", "=", "posted"],
            ["commitment_id", "!=", false],
            ["account_fiscal_year_id", "=", this.state.fiscalYearId],
            ["move_type", "=", moveType],
            ...this._drillLeaves(row),
            ...this._dimDomain(this._drillExclude),
        ];
        this._openDrill(
            `${this._drillName(row)} — ${USAGE_LABELS[moveType]}`,
            "budget.move.line",
            domain
        );
    },

    drillReturned(row) {
        const domain = [
            ["parent_state", "=", "posted"],
            ["commitment_id", "!=", false],
            ["account_fiscal_year_id", "=", this.state.fiscalYearId],
            ["is_return", "=", true],
            ...this._drillLeaves(row),
            ...this._dimDomain(this._drillExclude),
        ];
        this._openDrill(
            `${this._drillName(row)} — ส่งคืนเงินเหลือจ่าย`,
            "budget.move.line",
            domain
        );
    },
});

patch(BudgetOverview.prototype, "budget_ledger.BudgetOverview", {
    openSectionItem(section, item, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        if (!item || !item.id) {
            return; // the aggregated "อื่น ๆ" row (id === false)
        }
        const domain = [
            [section.drill_dim, "=", item.id],
            ["parent_state", "=", "posted"],
            ["commitment_id", "!=", false],
            ["account_fiscal_year_id", "=", this.state.fiscalYearId],
        ];
        if (this.state.sourceId) {
            domain.push(["source_analytic_id", "=", this.state.sourceId]);
        }
        const dep = this._deptDrillLeaf();
        if (dep) {
            domain.push(dep);
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `${item.code || ""} ${item.name || ""}`.trim(),
            res_model: "budget.move.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain,
            target: "current",
        });
    },
});
