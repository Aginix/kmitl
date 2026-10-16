/** @odoo-module */

import {Component, useState} from "@odoo/owl";
import {formatDateTime} from "@web/core/l10n/dates";
import {registry} from "@web/core/registry";
import {standardWidgetProps} from "@web/views/widgets/standard_widget_props";

const moneyFormat = new Intl.NumberFormat("th-TH", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
});

/**
 * จัดสรรงบประมาณ (งบลอย) — the bank-app style body of the wizard (ADR-0009).
 *
 * Renders the three steps from the wizard record: ``input`` (FROM the floating
 * pool → TO the project, with the amount typed here and the after-transfer
 * balances recomputed live), ``review`` (a receipt) and ``done`` (the slip).
 * The amount is written back with ``record.update`` so the footer buttons save it.
 */
export class FloatingAllocationWidget extends Component {
    setup() {
        const amount = this.props.record.data.amount;
        this.state = useState({raw: amount ? moneyFormat.format(amount) : ""});
    }

    get data() {
        return this.props.record.data;
    }
    get amount() {
        return this.data.amount || 0;
    }
    get floatingAfter() {
        return this.data.floating_available - this.amount;
    }
    get projectAfter() {
        return this.data.project_received + this.amount;
    }
    get isOverAvailable() {
        return this.amount - this.data.floating_available > 0.005;
    }
    get isOverPlan() {
        return (
            this.data.plan_total > 0 && this.projectAfter - this.data.plan_total > 0.005
        );
    }
    get transferDate() {
        return this.data.transfer_date ? formatDateTime(this.data.transfer_date) : "";
    }
    get transferUser() {
        const user = this.data.transfer_user_id;
        return (user && user[1]) || "";
    }

    money(value) {
        return moneyFormat.format(value || 0);
    }

    onAmountInput(ev) {
        const raw = ev.target.value.replace(/[^\d.,]/g, "");
        this.state.raw = raw;
        const value = parseFloat(raw.replace(/,/g, ""));
        this.props.record.update({amount: Number.isFinite(value) ? value : 0});
    }

    onAmountBlur() {
        this.state.raw = this.amount ? moneyFormat.format(this.amount) : "";
    }
}

FloatingAllocationWidget.template =
    "kmitl_project_floating_allocation.FloatingAllocation";
FloatingAllocationWidget.props = {...standardWidgetProps};

registry
    .category("view_widgets")
    .add("kmitl_floating_allocation", FloatingAllocationWidget);
