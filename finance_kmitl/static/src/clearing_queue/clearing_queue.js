/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart } from "@odoo/owl";
// eslint-disable-next-line max-len
import { MultiRecordSelect } from "@accounting_kmitl_workflow/approval_queue/multi_record_select";

/**
 * ใบล้างเจ้าหนี้ — the accounting office's register of the vouchers that clear a
 * payable, and their work surface over them.
 *
 * Read off **account.payment** rather than account.move even though the menu is
 * about the entries: one payment is one clearing voucher, and the payment is the
 * record that carries *both* offices' statuses (the finance office's own
 * ``finance_state`` and the accounting office's ``display_state``) plus the หัวจ่าย
 * the money left from. Reading the move instead would mean a second round trip for
 * every one of those columns. Opening a row still opens the journal entry — that is
 * the document being registered.
 *
 * Mirrors accounting_kmitl_workflow's approval queue in shape (filter bar,
 * expandable rows showing the journal items, per-row and batch action) and reuses
 * both its MultiRecordSelect and its stylesheet classes, which are in the same
 * backend bundle.
 */
const PAYMENT_FIELDS = [
    "name",
    "date",
    "partner_id",
    "amount",
    "payment_method_line_id",
    "finance_state",
    "display_state",
    "state",
    "workflow_state",
    "move_id",
    "submitted_by",
    "department_analytic_id",
    "fund_analytic_id",
    "source_analytic_id",
    "activity_analytic_id",
];

const LINE_FIELDS = ["account_id", "name", "debit", "credit"];

// Filter buckets backed by the MultiRecordSelect widget -> payment field.
const FILTER_FIELDS = {
    departments: "department_analytic_id",
    sources: "source_analytic_id",
    funds: "fund_analytic_id",
    activities: "activity_analytic_id",
    payingAccounts: "payment_method_line_id",
    partners: "partner_id",
};

// The stages a clearing voucher is looked for in. Phrased as the question being
// asked rather than as the field values behind it.
const STAGES = {
    all: [],
    to_book: [
        ["finance_state", "=", "paid"],
        ["state", "=", "draft"],
    ],
    to_approve: [["workflow_state", "=", "to_approve"]],
    posted: [["state", "=", "posted"]],
};

export class ClearingQueue extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.company = useService("company");
        this.fiscalYears = [];
        this.state = useState({
            loading: true,
            payments: [],
            expandedId: null,
            linesByPayment: {},
            selectedIds: [],
            stage: "to_book",
            fiscalYearId: false,
            dateFrom: false,
            dateTo: false,
            showAdvanced: false,
            departments: [],
            sources: [],
            funds: [],
            activities: [],
            payingAccounts: [],
            partners: [],
        });
        this.labels = {
            title: _t("Vendor Clearing Vouchers"),
            submitSelected: _t("Submit Selected"),
            empty: _t("No clearing voucher here."),
            number: _t("Number"),
            date: _t("Date"),
            payee: _t("Payee"),
            payingAccount: _t("Paying Account"),
            amount: _t("Amount"),
            financeState: _t("Finance Status"),
            accountingState: _t("Accounting Status"),
            actions: _t("Actions"),
            open: _t("Open"),
            submit: _t("Submit"),
            submittedBy: _t("Submitted By"),
            account: _t("Account"),
            label: _t("Label"),
            debit: _t("Debit"),
            credit: _t("Credit"),
            department: _t("Department"),
            source: _t("Source"),
            fund: _t("Fund"),
            activity: _t("Activity"),
            fiscalYear: _t("Fiscal Year"),
            dateFrom: _t("Date From"),
            dateTo: _t("Date To"),
            departments: _t("Departments"),
            sources: _t("Sources"),
            funds: _t("Funds"),
            activities: _t("Activities"),
            payingAccounts: _t("Paying Accounts"),
            partners: _t("Payees"),
            moreFilters: _t("More filters"),
            hideFilters: _t("Hide filters"),
            stageAll: _t("All"),
            stageToBook: _t("To book"),
            stageToApprove: _t("Awaiting approval"),
            stagePosted: _t("Posted"),
        };
        onWillStart(async () => {
            this.companyId = this.company.currentCompany.id;
            this.fiscalYears = await this.orm.searchRead(
                "account.fiscal.year",
                [],
                ["id", "name", "date_from", "date_to"],
                { order: "date_from desc" }
            );
            await this.load();
        });
    }

    get domain() {
        // The same set the menu has always shown: what an outbound payment to a
        // vendor books, which is what clears a payable.
        const domain = [
            ["partner_type", "=", "supplier"],
            ["payment_type", "=", "outbound"],
            ...(STAGES[this.state.stage] || []),
        ];
        if (this.state.dateFrom) {
            domain.push(["date", ">=", this.state.dateFrom]);
        }
        if (this.state.dateTo) {
            domain.push(["date", "<=", this.state.dateTo]);
        }
        for (const [key, field] of Object.entries(FILTER_FIELDS)) {
            const ids = this.state[key].map((record) => record.id);
            if (ids.length) {
                domain.push([field, "in", ids]);
            }
        }
        return domain;
    }

    async load() {
        this.state.loading = true;
        this.state.payments = await this.orm.searchRead(
            "account.payment",
            this.domain,
            PAYMENT_FIELDS,
            { order: "date desc, id desc" }
        );
        const ids = this.state.payments.map((payment) => payment.id);
        this.state.selectedIds = this.state.selectedIds.filter((id) =>
            ids.includes(id)
        );
        this.state.expandedId = null;
        this.state.loading = false;
    }

    // ------------------------------------------------------------------
    // Filters
    // ------------------------------------------------------------------
    setStage(stage) {
        this.state.stage = stage;
        this.load();
    }

    isStage(stage) {
        return this.state.stage === stage;
    }

    onFiscalYearChange(ev) {
        const id = parseInt(ev.target.value) || false;
        this.state.fiscalYearId = id;
        const fy = this.fiscalYears.find((f) => f.id === id);
        this.state.dateFrom = fy ? fy.date_from : false;
        this.state.dateTo = fy ? fy.date_to : false;
        this.load();
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value || false;
        this.load();
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value || false;
        this.load();
    }

    toggleAdvanced() {
        this.state.showAdvanced = !this.state.showAdvanced;
    }

    onSelectionChange(key, selected) {
        if (Object.prototype.hasOwnProperty.call(FILTER_FIELDS, key)) {
            this.state[key] = selected;
            this.load();
        }
    }

    isFiscalYearSelected(fyId) {
        return fyId === this.state.fiscalYearId;
    }

    // ------------------------------------------------------------------
    // Rows
    // ------------------------------------------------------------------
    moveId(payment) {
        return Array.isArray(payment.move_id) ? payment.move_id[0] : payment.move_id;
    }

    openMove(payment) {
        // The journal entry, not the payment: this register is about the entries,
        // and the entry is where the accounting office does its work.
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: this.moveId(payment),
            views: [[false, "form"]],
            target: "current",
        });
    }

    async toggleExpand(payment) {
        if (this.state.expandedId === payment.id) {
            this.state.expandedId = null;
            return;
        }
        if (!this.state.linesByPayment[payment.id]) {
            this.state.linesByPayment[payment.id] = await this.orm.searchRead(
                "account.move.line",
                [
                    ["move_id", "=", this.moveId(payment)],
                    ["display_type", "not in", ["line_section", "line_note"]],
                ],
                LINE_FIELDS
            );
        }
        this.state.expandedId = payment.id;
    }

    /**
     * A voucher is the accounting maker's to submit once the finance office has
     * handed it over and nobody has submitted it yet. Everything else on this
     * register is either still the finance office's or already past this step.
     */
    canSubmit(payment) {
        return payment.finance_state === "paid" && payment.state === "draft";
    }

    get submittableIds() {
        return this.state.payments
            .filter(
                (payment) =>
                    this.state.selectedIds.includes(payment.id) &&
                    this.canSubmit(payment)
            )
            .map((payment) => this.moveId(payment));
    }

    async submit(payment) {
        const result = await this.orm.call("account.move", "action_submit", [
            [this.moveId(payment)],
        ]);
        if (result && typeof result === "object") {
            // base_exception wants to show its popup — with one row in hand there
            // is somebody to show it to.
            await this.action.doAction(result, { onClose: () => this.load() });
            return;
        }
        this.notification.add(_t("Submitted"), { type: "success" });
        await this.load();
    }

    async submitSelected() {
        const ids = this.submittableIds;
        if (!ids.length) {
            return;
        }
        const action = await this.orm.call("account.move", "action_submit_batch", [
            ids,
        ]);
        if (action) {
            await this.action.doAction(action);
        }
        await this.load();
    }

    toggleSelect(paymentId) {
        const selected = this.state.selectedIds;
        this.state.selectedIds = selected.includes(paymentId)
            ? selected.filter((id) => id !== paymentId)
            : [...selected, paymentId];
    }

    isSelected(paymentId) {
        return this.state.selectedIds.includes(paymentId);
    }

    toggleSelectAll() {
        this.state.selectedIds = this.allSelected
            ? []
            : this.state.payments.map((payment) => payment.id);
    }

    get allSelected() {
        return (
            this.state.payments.length > 0 &&
            this.state.selectedIds.length === this.state.payments.length
        );
    }

    displayName(value) {
        return Array.isArray(value) ? value[1] : "";
    }

    formatCurrency(amount) {
        return (amount || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    financeBadge(payment) {
        return {
            draft: "text-bg-light",
            confirmed: "text-bg-warning",
            paid: "text-bg-success",
        }[payment.finance_state] || "text-bg-light";
    }

    accountingBadge(payment) {
        return {
            draft: "text-bg-light",
            to_approve: "text-bg-warning",
            submitted: "text-bg-info",
            posted: "text-bg-success",
            cancel: "text-bg-danger",
        }[payment.display_state] || "text-bg-light";
    }
}

ClearingQueue.template = "finance_kmitl.ClearingQueue";
ClearingQueue.components = { MultiRecordSelect };
ClearingQueue.props = ["*"];

registry.category("actions").add("finance_kmitl.clearing_queue", ClearingQueue);
