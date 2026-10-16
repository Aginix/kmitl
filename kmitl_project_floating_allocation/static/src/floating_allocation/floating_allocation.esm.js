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
 * จัดสรรงบประมาณ (งบลอย) — the body of the wizard (ADR-0009).
 *
 * Renders the three steps from the wizard record: ``input`` (FROM the floating
 * pool → TO the project, side by side, with the amount typed here and the
 * after-transfer balances recomputed live), ``review`` (a short summary) and
 * ``done`` (the slip). The amount is written back with ``record.update`` so the
 * footer buttons save it.
 */
export class FloatingAllocationWidget extends Component {
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
    get fromDims() {
        return parseDims(this.data.posted_pool_dims || this.data.pool_dims);
    }
    get toDims() {
        return parseDims(this.data.project_dims);
    }
    get isExhausted() {
        return this.data.pool_found && this.data.floating_available <= 0.005;
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
