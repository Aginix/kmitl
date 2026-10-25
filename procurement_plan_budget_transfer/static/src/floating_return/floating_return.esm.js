/** @odoo-module */

import {Component, useState} from "@odoo/owl";
import {formatDateTime} from "@web/core/l10n/dates";
import {registry} from "@web/core/registry";
import {standardWidgetProps} from "@web/views/widgets/standard_widget_props";

const moneyFormat = new Intl.NumberFormat("th-TH", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
});

const STEPS = ["กรอกจำนวนเงิน", "ตรวจสอบ", "สำเร็จ"];
const STEP_INDEX = {input: 0, review: 1, done: 2};

function parseDims(json) {
    try {
        return JSON.parse(json || "[]");
    } catch {
        return [];
    }
}

/**
 * โอนคืนงบลอย of a procurement plan — the body of the wizard. The same three
 * steps as KMITL Project's floating wizard, implemented separately
 * (procurement_plan ADR-0006): ``input`` (FROM the plan → TO the floating pool,
 * side by side, the amount typed here and the balances after the return
 * recomputed live), ``review`` and ``done`` (the slip). The amount is written
 * back with ``record.update`` so the footer buttons save it.
 */
export class PlanFloatingReturnWidget extends Component {
    setup() {
        this.steps = STEPS;
        const amount = this.props.record.data.amount;
        this.state = useState({raw: amount ? moneyFormat.format(amount) : ""});
    }

    get data() {
        return this.props.record.data;
    }
    get stepIndex() {
        return STEP_INDEX[this.data.step] || 0;
    }
    get amount() {
        return this.data.amount || 0;
    }
    get poolDims() {
        return parseDims(this.data.posted_pool_dims || this.data.pool_dims);
    }
    get planDims() {
        return parseDims(this.data.plan_dims);
    }
    get isExhausted() {
        return this.data.returnable <= 0.005;
    }
    get returnableAfter() {
        return this.data.returnable - this.amount;
    }
    get planAfter() {
        return this.data.plan_received - this.amount;
    }
    get isOverAvailable() {
        return this.amount - this.data.returnable > 0.005;
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

    /**
     * "[code] leaf" of the budget code row, for the short summary lines.
     *
     * @param {Array} dims rows from the wizard's *_dims JSON
     * @returns {String}
     */
    budgetCode(dims) {
        const row = dims.find((d) => d.key === "account_id");
        return row ? `[${row.code}] ${row.leaf}` : "";
    }

    onAmountInput(ev) {
        const raw = ev.target.value.replace(/[^\d.,]/g, "");
        this.state.raw = raw;
        const value = parseFloat(raw.replace(/,/g, ""));
        this.props.record.update({amount: Number.isFinite(value) ? value : 0});
    }

    onFillMax() {
        const value = this.data.returnable || 0;
        this.state.raw = moneyFormat.format(value);
        this.props.record.update({amount: value});
    }

    onAmountBlur() {
        this.state.raw = this.amount ? moneyFormat.format(this.amount) : "";
    }
}

PlanFloatingReturnWidget.template = "procurement_plan_budget_transfer.FloatingReturn";
PlanFloatingReturnWidget.props = {...standardWidgetProps};

registry
    .category("view_widgets")
    .add("procurement_plan_floating_return", PlanFloatingReturnWidget);
