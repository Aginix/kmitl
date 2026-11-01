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
 * บัญชีโครงการ summary (ADR-0012): ได้รับจัดสรร › จองแล้ว › เบิกจ่ายแล้ว = คงเหลือ,
 * where คงเหลือ = ได้รับ − เบิกจ่าย, and a bar of the received money split into
 * consumed / remaining / remaining-but-not-reserved, against the estimate.
 */
export class BudgetOverviewSummary extends Component {
    get data() {
        return this.props.record.data;
    }
    money(value) {
        return moneyFormat.format(value || 0);
    }
    get estimatePct() {
        return Math.round(pct(this.data.budget_amount, this.data.budget_estimate));
    }
    get unreserved() {
        // Only a gap once the project has reserved and is spending.
        const d = this.data;
        if (d.state !== "in_progress" || d.budget_reserved_total <= 0) {
            return 0;
        }
        return Math.min(d.budget_unreserved, Math.max(d.budget_remaining, 0));
    }
    get bar() {
        const d = this.data;
        const base = Math.max(d.budget_estimate, d.budget_amount, 0);
        const remaining = Math.max(d.budget_remaining, 0);
        return {
            show: base > 0,
            consumed: pct(d.budget_consumed, base),
            remaining: pct(remaining - this.unreserved, base),
            unreserved: pct(this.unreserved, base),
            notReceived: d.budget_estimate > d.budget_amount,
        };
    }
}

BudgetOverviewSummary.template = "kmitl_project_budget_overview.Summary";
BudgetOverviewSummary.props = {...standardWidgetProps};

registry
    .category("view_widgets")
    .add("kmitl_project_budget_overview_summary", BudgetOverviewSummary);
