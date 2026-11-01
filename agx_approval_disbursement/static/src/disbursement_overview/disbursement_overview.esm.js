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
 * ภาพรวมการเบิกจ่าย (agx_approval ADR-0010): ยอดอนุมัติ − เบิกจ่ายแล้ว −
 * อยู่ระหว่างเบิก = คงเหลือ, per request and per Expense, and the request's
 * ใบขอเบิก. Fed by the read-as-superuser ``disbursement_overview`` field, so
 * the requester sees it too; DR links only for users who may open one.
 */
export class DisbursementOverview extends Component {
    get data() {
        return this.props.record.data.disbursement_overview || false;
    }
    money(value) {
        return moneyFormat.format(value || 0);
    }
    get bar() {
        const d = this.data;
        const base = Math.max(d.approved, d.disbursed + d.in_progress, 0);
        return {
            disbursed: pct(d.disbursed, base),
            inProgress: pct(d.in_progress, base),
            closed: pct(d.closed, base),
            remaining: pct(Math.max(d.remaining, 0), base),
        };
    }
    get closedLabel() {
        if (this.data.returned) {
            return "ส่งคืนเงินเหลือจ่าย";
        }
        return this.data.shared ? "คืนใบจองร่วม" : "ปิดยอด";
    }
    get totals() {
        const sum = (key) => this.data.expenses.reduce((a, e) => a + e[key], 0);
        return {
            amount: sum("amount"),
            disbursed: sum("disbursed"),
            inProgress: sum("in_progress"),
            remaining: sum("remaining"),
        };
    }
    drUrl(dr) {
        return `/web#id=${dr.id}&model=disbursement.request&view_type=form`;
    }
}

DisbursementOverview.props = {...standardWidgetProps};

/** The figures and alerts, under the request's title. */
export class DisbursementOverviewSummary extends DisbursementOverview {}
DisbursementOverviewSummary.template = "agx_approval_disbursement.OverviewSummary";

/** The Expense and ใบขอเบิก tables, in the การเบิกจ่าย tab. */
export class DisbursementOverviewDetail extends DisbursementOverview {}
DisbursementOverviewDetail.template = "agx_approval_disbursement.OverviewDetail";

registry
    .category("view_widgets")
    .add("agx_approval_disbursement_overview_summary", DisbursementOverviewSummary)
    .add("agx_approval_disbursement_overview_detail", DisbursementOverviewDetail);
