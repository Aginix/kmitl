/** @odoo-module **/

import {Component} from "@odoo/owl";
import {formatDateTime} from "@web/core/l10n/dates";
import {registry} from "@web/core/registry";
import {standardWidgetProps} from "@web/views/widgets/standard_widget_props";

const moneyFormat = new Intl.NumberFormat("th-TH", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
});

const STEPS = ["ตรวจสอบ", "สำเร็จ"];
const STEP_INDEX = {review: 0, done: 1};

/**
 * ส่งคืนเงินเหลือจ่าย — the body of budget.commitment.return.wizard, styled
 * after kmitl_project_budget_transfer's โอนคืนงบลอย: ``review`` shows the money
 * leaving the reservation (FROM card) back to the budget at the same
 * coordinate (TO card), ``done`` is the slip. The amount is typed in the
 * wizard's ``amount`` field (default: the whole leftover, ``return_amount``).
 */
export class BudgetCommitmentReturnWidget extends Component {
    setup() {
        this.steps = STEPS;
    }

    get data() {
        return this.props.record.data;
    }
    get stepIndex() {
        return STEP_INDEX[this.data.step] || 0;
    }
    get dims() {
        try {
            return JSON.parse(this.data.commitment_dims || "[]");
        } catch {
            return [];
        }
    }
    get amount() {
        return this.data.step === "done" ? this.data.returned_amount : this.data.amount;
    }
    // Leftover still reserved after this return.
    get remaining() {
        return (this.data.return_amount || 0) - (this.data.amount || 0);
    }
    get isPartial() {
        return this.remaining > 0.005;
    }
    get isInvalid() {
        return this.remaining < -0.005 || (this.data.amount || 0) <= 0;
    }
    get budgetCode() {
        const row = this.dims.find((d) => d.key === "account_id");
        return row ? `[${row.code}] ${row.leaf}` : "";
    }
    // A partial return, or an open obligation, keeps the commitment open.
    get closesCommitment() {
        return !this.isPartial && (this.data.available_to_consume || 0) <= 0.005;
    }
    get returnDate() {
        return this.data.return_date ? formatDateTime(this.data.return_date) : "";
    }
    get returnUser() {
        const user = this.data.return_user_id;
        return (user && user[1]) || "";
    }

    money(value) {
        return moneyFormat.format(value || 0);
    }
}

BudgetCommitmentReturnWidget.template = "budget.CommitmentReturn";
BudgetCommitmentReturnWidget.props = {...standardWidgetProps};

registry
    .category("view_widgets")
    .add("budget_commitment_return", BudgetCommitmentReturnWidget);
