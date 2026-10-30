/** @odoo-module */

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {standardWidgetProps} from "@web/views/widgets/standard_widget_props";

const moneyFormat = new Intl.NumberFormat("th-TH", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
});

function pct(part, whole) {
    return whole > 0 ? Math.max(0, Math.min(100, (part / whole) * 100)) : 0;
}

/**
 * บัญชีแผน summary: ได้รับจัดสรร − เบิกจ่ายแล้ว = คงเหลือ, and a bar of the
 * received money split into consumed / remaining / remaining-but-not-reserved,
 * against the Plan Amount (วงเงินตามแผน).
 */
export class PlanBudgetOverviewSummary extends Component {
    get data() {
        return this.props.record.data;
    }
    money(value) {
        return moneyFormat.format(value || 0);
    }
    get planPct() {
        return Math.round(pct(this.data.budget_amount, this.data.total_price));
    }
    get unreserved() {
        // Only a gap once the plan has reserved and is spending.
        const d = this.data;
        if (d.state !== "in_progress" || d.budget_reserved_total <= 0) {
            return 0;
        }
        return Math.min(d.budget_unreserved, Math.max(d.budget_remaining, 0));
    }
    get bar() {
        const d = this.data;
        const base = Math.max(d.total_price, d.budget_amount, 0);
        const remaining = Math.max(d.budget_remaining, 0);
        return {
            show: base > 0,
            consumed: pct(d.budget_consumed, base),
            remaining: pct(remaining - this.unreserved, base),
            unreserved: pct(this.unreserved, base),
            notReceived: d.total_price > d.budget_amount,
        };
    }
}

PlanBudgetOverviewSummary.template = "procurement_plan_budget_overview.Summary";
PlanBudgetOverviewSummary.props = {...standardWidgetProps};

registry
    .category("view_widgets")
    .add("procurement_plan_budget_overview_summary", PlanBudgetOverviewSummary);
